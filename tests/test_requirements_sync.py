"""requirements.txt must match pyproject.toml [project.dependencies] (same packages)."""

from pathlib import Path

import tomli as tomllib


def _normalized_package_name(spec: str) -> str:
    spec = spec.strip().strip('"').strip("'")
    for sep in (">=", "~=", "==", "<", ">"):
        if sep in spec:
            spec = spec.split(sep, 1)[0].strip()
            break
    bracket = spec.find("[")
    if bracket != -1:
        spec = spec[:bracket].strip()
    return spec.lower().replace("_", "-")


def test_requirements_txt_matches_pyproject_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject_path = root.joinpath("pyproject.toml")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    pyproject_deps = data["project"]["dependencies"]
    pyproject_names = {_normalized_package_name(x) for x in pyproject_deps}

    req_names: set[str] = set()
    for line in root.joinpath("requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        req_names.add(_normalized_package_name(line))

    assert pyproject_names == req_names, (
        f"only in pyproject.toml: {pyproject_names - req_names}; "
        f"only in requirements.txt: {req_names - pyproject_names}"
    )
