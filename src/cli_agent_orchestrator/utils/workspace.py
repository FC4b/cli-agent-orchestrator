"""VS Code workspace file (.code-workspace) parser and utilities."""

import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkspaceFolder(BaseModel):
    """A folder in a VS Code workspace."""

    path: str
    name: Optional[str] = None

    def resolve(self, workspace_dir: Path) -> Path:
        """Resolve the folder path relative to the workspace file directory."""
        folder_path = Path(self.path)
        if folder_path.is_absolute():
            return folder_path
        return (workspace_dir / folder_path).resolve()


class VSCodeWorkspace(BaseModel):
    """VS Code workspace file model."""

    folders: List[WorkspaceFolder] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)

    # CAO-specific fields (can be embedded in workspace settings)
    cao_agents: Optional[List[dict]] = None


def parse_workspace_file(workspace_path: Path) -> VSCodeWorkspace:
    """Parse a .code-workspace file.

    Args:
        workspace_path: Path to the .code-workspace file

    Returns:
        VSCodeWorkspace model with parsed data

    Raises:
        FileNotFoundError: If workspace file doesn't exist
        ValueError: If file is not valid JSON or missing required fields
    """
    if not workspace_path.exists():
        raise FileNotFoundError(f"Workspace file not found: {workspace_path}")

    if not workspace_path.suffix == ".code-workspace":
        raise ValueError(f"Expected .code-workspace file, got: {workspace_path.suffix}")

    try:
        with open(workspace_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in workspace file: {e}")

    # Parse folders
    folders = []
    for folder_data in data.get("folders", []):
        if isinstance(folder_data, dict):
            folders.append(WorkspaceFolder(**folder_data))
        elif isinstance(folder_data, str):
            folders.append(WorkspaceFolder(path=folder_data))

    # Check for CAO config in settings
    settings = data.get("settings", {})
    cao_config = settings.get("cao", {})
    cao_agents = cao_config.get("agents") if cao_config else None

    return VSCodeWorkspace(
        folders=folders,
        settings=settings,
        cao_agents=cao_agents,
    )


def get_workspace_folders(workspace_path: Path) -> List[Path]:
    """Get resolved folder paths from a workspace file.

    Args:
        workspace_path: Path to the .code-workspace file

    Returns:
        List of resolved absolute paths to workspace folders
    """
    workspace = parse_workspace_file(workspace_path)
    workspace_dir = workspace_path.parent

    resolved_folders = []
    for folder in workspace.folders:
        resolved = folder.resolve(workspace_dir)
        if resolved.exists():
            resolved_folders.append(resolved)

    return resolved_folders


def get_workspace_root(workspace_path: Path) -> Path:
    """Get the root directory of the workspace (directory containing .code-workspace file).

    Args:
        workspace_path: Path to the .code-workspace file

    Returns:
        Path to the workspace root directory
    """
    return workspace_path.parent.resolve()


def create_workspace_context(workspace_path: Path) -> dict:
    """Create a context dictionary with workspace information for agents.

    Args:
        workspace_path: Path to the .code-workspace file

    Returns:
        Dictionary with workspace context information
    """
    workspace = parse_workspace_file(workspace_path)
    workspace_dir = workspace_path.parent

    folders_info = []
    for folder in workspace.folders:
        resolved = folder.resolve(workspace_dir)
        folders_info.append({
            "path": str(resolved),
            "name": folder.name or resolved.name,
            "exists": resolved.exists(),
        })

    return {
        "workspace_file": str(workspace_path.resolve()),
        "workspace_root": str(workspace_dir.resolve()),
        "folders": folders_info,
        "folder_count": len(folders_info),
    }


def write_workspace_context_file(workspace_path: Path, output_dir: Path) -> Path:
    """Write workspace context to a JSON file that agents can read.

    Args:
        workspace_path: Path to the .code-workspace file
        output_dir: Directory to write the context file

    Returns:
        Path to the created context file
    """
    context = create_workspace_context(workspace_path)
    output_file = output_dir / ".cao-workspace-context.json"

    with open(output_file, "w") as f:
        json.dump(context, f, indent=2)

    return output_file


