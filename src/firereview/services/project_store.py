import json

from ..models import DrawingModel


def save_project(model: DrawingModel, file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(model.to_dict(), file, ensure_ascii=False, indent=2)


def load_project(file_path: str) -> DrawingModel:
    with open(file_path, "r", encoding="utf-8") as file:
        return DrawingModel.from_dict(json.load(file))
