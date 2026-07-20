import os
from dotenv import load_dotenv
import requests
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
from collections import defaultdict

# -----------------------------------
# ENV 로딩
# -----------------------------------
load_dotenv()

GITLAB_URL = os.getenv("GITLAB_URL")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
NAMESPACE_PREFIX = os.getenv("GITLAB_NAMESPACE_PREFIX")

if not GITLAB_URL or not GITLAB_TOKEN:
    raise RuntimeError("GITLAB_URL / GITLAB_TOKEN 이 설정되지 않았습니다 (.env 확인)")

SESSION = requests.Session()
SESSION.headers.update({
    "PRIVATE-TOKEN": GITLAB_TOKEN
})

# ===========================
# GitLab API helper
# ===========================

def gitlab_get(path, params=None):
    url = f"{GITLAB_URL}/api/v4{path}"
    all_results = []
    page = 1
    per_page = 100

    while True:
        p = params.copy() if params else {}
        p.update({"page": page, "per_page": per_page})
        resp = SESSION.get(url, params=p)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            all_results.extend(data)
        else:
            return data

        if len(data) < per_page:
            break
        page += 1

    return all_results


def list_projects():
    projects = gitlab_get(
        "/projects",
        {"membership": True, "simple": True, "archived": False}
    )
    if NAMESPACE_PREFIX:
        projects = [
            p for p in projects
            if p.get("path_with_namespace", "").startswith(NAMESPACE_PREFIX)
        ]
    return projects


def get_default_branch(project_id):
    proj = gitlab_get(f"/projects/{project_id}")
    return proj.get("default_branch")


def list_repo_files(project_id, ref):
    return gitlab_get(
        f"/projects/{project_id}/repository/tree",
        {"ref": ref, "recursive": True}
    )


def get_file_raw(project_id, ref, path):
    url_path = urllib.parse.quote(path, safe="")
    resp = SESSION.get(
        f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/files/{url_path}/raw",
        params={"ref": ref},
    )
    if resp.status_code == 200:
        return resp.text
    return None


# ===========================
# 공통: 결과 레코드 구조
# ===========================

def make_dep(ecosystem, group, name, version, raw=None, language=None):
    """
    통일된 형태의 dependency dict 생성
    """
    return {
        "ecosystem": ecosystem,   # e.g. nuget, maven, gradle, sbt, vcpkg, conan, cmake_find_package
        "language": language,     # optional: c, csharp, java, scala
        "group": group,
        "name": name,             # artifact or package name
        "version": version,
        "raw": raw or ""
    }


# ===========================
# C# 파서
# ===========================

def parse_csproj_or_props_xml(content):
    deps = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return deps

    # PackageReference
    for pr in root.findall(".//{*}PackageReference"):
        name = pr.get("Include") or pr.get("Update")
        version = pr.get("Version")
        if name:
            deps.append(
                make_dep("nuget", None, name, version, raw=ET.tostring(pr, encoding="unicode"),
                         language="csharp")
            )
    return deps


def parse_packages_config(content):
    deps = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return deps

    for pkg in root.findall(".//package"):
        name = pkg.get("id")
        version = pkg.get("version")
        if name:
            deps.append(
                make_dep("nuget", None, name, version,
                         raw=ET.tostring(pkg, encoding="unicode"),
                         language="csharp")
            )
    return deps


# ===========================
# C/C++ 파서
# ===========================

def parse_vcpkg_json(content):
    deps = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return deps

    for dep in data.get("dependencies", []):
        if isinstance(dep, str):
            deps.append(
                make_dep("vcpkg", None, dep, None, raw=dep, language="c")
            )
        elif isinstance(dep, dict):
            name = dep.get("name")
            version = dep.get("version") or dep.get("version>=")
            if name:
                deps.append(
                    make_dep("vcpkg", None, name, version, raw=json.dumps(dep), language="c")
                )
    return deps


def parse_conanfile_txt(content):
    deps = []
    in_requires = False
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("[requires]"):
            in_requires = True
            continue
        if line.startswith("[") and line.endswith("]") and line.lower() != "[requires]":
            in_requires = False
            continue
        if in_requires:
            # 예: fmt/8.1.1@, openssl/3.0.0
            raw = line
            deps.append(
                make_dep("conan", None, line, None, raw=raw, language="c")
            )
    return deps


FIND_PACKAGE_RE = re.compile(
    r"find_package\(\s*([A-Za-z0-9_\.]+)(?:[^)]*VERSION\s+([0-9][^)\s]*))?",
    re.IGNORECASE
)

def parse_cmakelists(content):
    deps = []
    for m in FIND_PACKAGE_RE.finditer(content):
        name = m.group(1)
        version = m.group(2)
        deps.append(
            make_dep("cmake_find_package", None, name, version, raw=m.group(0), language="c")
        )
    return deps


# ===========================
# Maven (Java/Scala)
# ===========================

def parse_pom_xml(content):
    deps = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return deps

    ns = {"m": root.tag[1:].split("}")[0]} if root.tag.startswith("{") else {}

    def findall(elem, path):
        if ns:
            return elem.findall(path.format(ns="m"), ns)
        return elem.findall(path.format(ns=""))

    # <dependencies>와 <dependencyManagement>/<dependencies> 모두
    for deps_parent in findall(root, ".//{ns}dependencies"):
        for d in deps_parent.findall("./{*}dependency"):
            group = d.findtext("./{*}groupId")
            artifact = d.findtext("./{*}artifactId")
            version = d.findtext("./{*}version")
            scope = d.findtext("./{*}scope") or ""
            if group and artifact:
                # 언어는 일단 java로 두고, 나중에 sbt/scala 관련 파일이 같이 있으면 scala로 추가 분류 가능
                deps.append(
                    make_dep(
                        "maven",
                        group,
                        artifact,
                        version,
                        raw=ET.tostring(d, encoding="unicode"),
                        language="java"
                    )
                )
    return deps


# ===========================
# Gradle (Java/Scala)
# ===========================

# implementation 'group:artifact:version'
GRADLE_COORD_RE = re.compile(
    r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation|testCompile|compile)\s*
        \(?\s*['"]([^'":]+):([^'":]+):([^'"]+)['"]""",
    re.IGNORECASE | re.VERBOSE
)

def parse_gradle_build(content):
    deps = []
    for m in GRADLE_COORD_RE.finditer(content):
        group, artifact, version = m.group(1), m.group(2), m.group(3)
        deps.append(
            make_dep("gradle", group, artifact, version, raw=m.group(0), language="java")
        )
    return deps


# ===========================
# SBT (Scala)
# ===========================

# libraryDependencies += "org" %% "name" % "version"
SBT_DEP_RE = re.compile(
    r"""libraryDependencies\s*\+\=\s*["']([^"']+)["']\s*(%%|%)\s*["']([^"']+)["']\s*%\s*["']([^"']+)["']""",
    re.VERBOSE
)

def parse_sbt_build(content):
    deps = []
    for m in SBT_DEP_RE.finditer(content):
        group, pct, name, version = m.group(1), m.group(2), m.group(3), m.group(4)
        # %%인 경우에는 실제 artifact 이름이 name_scalaVersion 형태지만,
        # 일단 name만 기록해두고 나중에 필요하면 추가 분석
        deps.append(
            make_dep("sbt", group, name, version, raw=m.group(0), language="scala")
        )
    return deps


# ===========================
# 메인 스캐너
# ===========================

def scan():
    # key: project_name_with_namespace, value: list of (file_path, dep_dict)
    result = defaultdict(list)

    projects = list_projects()
    for proj in projects:
        pid = proj["id"]
        pname = proj["path_with_namespace"]
        default_branch = get_default_branch(pid)
        if not default_branch:
            continue

        print(f"[SCAN] {pname} ({default_branch})")
        try:
            tree = list_repo_files(pid, default_branch)
        except Exception as e:
            print(f"  ! failed to list tree: {e}")
            continue

        for item in tree:
            if item["type"] != "blob":
                continue
            path = item["path"]
            lower = path.lower()

            # C#
            if lower.endswith(".csproj") or lower.endswith(".fsproj") or lower.endswith(".props") or lower.endswith(".targets"):
                content = get_file_raw(pid, default_branch, path)
                if not content:
                    continue
                deps = parse_csproj_or_props_xml(content)
                for d in deps:
                    result[pname].append((path, d))

            elif lower.endswith("packages.config"):
                content = get_file_raw(pid, default_branch, path)
                if not content:
                    continue
                deps = parse_packages_config(content)
                for d in deps:
                    result[pname].append((path, d))

            # C / C++
            elif lower.endswith("vcpkg.json"):
                content = get_file_raw(pid, default_branch, path)
                if not content:
                    continue
                deps = parse_vcpkg_json(content)
                for d in deps:
                    result[pname].append((path, d))

            elif lower.endswith("conanfile.txt"):
                content = get_file_raw(pid, default_branch, path)
                if not content:
                    continue
                deps = parse_conanfile_txt(content)
                for d in deps:
                    result[pname].append((path, d))

            elif lower.endswith("cmakelists.txt"):
                content = get_file_raw(pid, default_branch, path)
                if not content:
                    continue
                deps = parse_cmakelists(content)
                for d in deps:
                    result[pname].append((path, d))

            # Maven
            elif lower.endswith("pom.xml"):
                content = get_file_raw(pid, default_branch, path)
                if not content:
                    continue
                deps = parse_pom_xml(content)
                for d in deps:
                    result[pname].append((path, d))

            # Gradle
            elif lower.endswith("build.gradle") or lower.endswith("build.gradle.kts"):
                content = get_file_raw(pid, default_branch, path)
                if not content:
                    continue
                deps = parse_gradle_build(content)
                for d in deps:
                    result[pname].append((path, d))

            # SBT
            elif lower.endswith("build.sbt") or lower.startswith("project/") and lower.endswith(".scala"):
                content = get_file_raw(pid, default_branch, path)
                if not content:
                    continue
                deps = parse_sbt_build(content)
                for d in deps:
                    result[pname].append((path, d))

        print(f"  -> {len(result[pname])} dependencies found.")

    return result


if __name__ == "__main__":
    deps_by_project = scan()

    # TSV로 인벤토리 저장
    out_file = "deps_inventory.tsv"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("project\tfile\tlanguage\tecosystem\tgroup\tname\tversion\traw\n")
        for proj, items in deps_by_project.items():
            for file_path, dep in items:
                f.write(
                    f"{proj}\t{file_path}\t{dep.get('language','')}\t"
                    f"{dep.get('ecosystem','')}\t{dep.get('group','')}\t"
                    f"{dep.get('name','')}\t{dep.get('version','')}\t"
                    f"{dep.get('raw','').replace(chr(9), ' ')}\n"
                )

    print(f"Done. See {out_file}")

