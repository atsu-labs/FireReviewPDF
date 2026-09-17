import json

from ..models import DrawingModel


def save_project(model: DrawingModel, file_path: str) -> None:
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(model.to_dict(), file, ensure_ascii=False, indent=2)
    except Exception as e:
        raise OSError(f"プロジェクトファイルの書き込みに失敗しました: {e}") from e


def load_project(file_path: str) -> DrawingModel:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except Exception as e:
                raise ValueError(f"プロジェクトファイルのJSON解析に失敗しました: {e}") from e
    except OSError as e:
        raise OSError(f"プロジェクトファイルの読み込みに失敗しました: {e}") from e

    try:
        return DrawingModel.from_dict(data)
    except Exception as e:
        raise ValueError(f"プロジェクトデータの復元に失敗しました: {e}") from e
