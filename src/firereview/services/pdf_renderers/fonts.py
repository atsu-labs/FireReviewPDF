import os
import fitz

_font_path_cache = {}


def get_windows_font_path(font_family_name: str):
    """動的にWindowsのレジストリから任意のフォントファミリー名に対応するフォントファイルパスを自動検出します。"""
    import sys
    if sys.platform != 'win32':
        return None
    if font_family_name in _font_path_cache:
        return _font_path_cache[font_family_name]

    import winreg
    path = None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts") as reg_key:
            num_values = winreg.QueryInfoKey(reg_key)[1]
            target = font_family_name.lower().strip()

            replacement_map = {
                "ゴシック": "gothic",
                "明朝": "mincho",
                "メイリオ": "meiryo",
                "游ゴシック": "yu gothic",
                "游明朝": "yu mincho"
            }

            targets = [target]
            for jp, en in replacement_map.items():
                if jp in target:
                    targets.append(target.replace(jp, en))

            for t in list(targets):
                no_space = t.replace(" ", "").replace("　", "")
                if no_space not in targets:
                    targets.append(no_space)

            for i in range(num_values):
                name, value, _ = winreg.EnumValue(reg_key, i)
                name_lower = name.lower()

                matched = False
                for t in targets:
                    name_no_space = name_lower.replace(" ", "").replace("　", "").replace(";", "")
                    if t in name_no_space:
                        matched = True
                        break

                if matched:
                    windir = os.environ.get('windir', 'C:/Windows')
                    sys_path = os.path.join(windir, "Fonts", value)
                    if os.path.exists(sys_path):
                        path = sys_path
                        break

                    user_profile = os.environ.get('USERPROFILE', 'C:/Users/Default')
                    user_path = os.path.join(user_profile, r"AppData/Local/Microsoft/Windows/Fonts", value)
                    if os.path.exists(user_path):
                        path = user_path
                        break

                    if os.path.exists(value):
                        path = os.path.abspath(value)
                        break
    except Exception:
        pass
    _font_path_cache[font_family_name] = path
    return path


def get_or_register_font(page_obj, page_idx: int, family_name: str, text_content: str, ann_type: str, registered_page_fonts: dict) -> str:
    """日本語フォントをロードしてPDFページに埋め込み登録します。"""
    if page_idx not in registered_page_fonts:
        registered_page_fonts[page_idx] = {}

    family_lower = (family_name or "Arial").lower().strip()
    has_japanese_text = False
    if text_content:
        has_japanese_text = any(char > '\u007f' for char in text_content)

    is_legend = (ann_type == "legend")
    need_japanese = (
        has_japanese_text
        or is_legend
        or any(x in family_lower for x in ["gothic", "ゴシック", "meiryo", "メイリオ", "yu", "游", "mincho", "明朝", "biz", "noto", "sans", "jp"])
    )

    if not need_japanese:
        return "helv"

    pdf_name = "bizudgothic"
    if pdf_name in registered_page_fonts[page_idx]:
        return registered_page_fonts[page_idx][pdf_name]

    font_path = get_windows_font_path("BIZ UD Gothic") or get_windows_font_path("BIZ UDゴシック")
    if not font_path:
        for fallback_name in ["MS Gothic", "Meiryo"]:
            font_path = get_windows_font_path(fallback_name)
            if font_path:
                break

    if not font_path:
        raise RuntimeError(
            "日本語を描画するための適切なシステムフォント（BIZ UDゴシック、MSゴシック、Meiryo等）がシステム内に検出されません。"
            "お使いのOSに日本語フォントが正しくインストールされているか確認してください。"
        )

    try:
        page_obj.insert_font(fontname=pdf_name, fontfile=font_path)
        registered_page_fonts[page_idx][pdf_name] = pdf_name
        return pdf_name
    except Exception as e:
        raise RuntimeError(
            f"日本語フォント（{font_path}）のPDFエクスポート用登録に失敗しました。"
            f"エラー詳細: {e}"
        )


def get_font_object(page_font: str) -> fitz.Font:
    """指定されたPDFフォント名に対応するfitz.Fontオブジェクトを取得します。"""
    if page_font == "helv":
        return fitz.Font(fontname="helv")

    f_path = get_windows_font_path("BIZ UD Gothic") or get_windows_font_path("BIZ UDゴシック")
    if not f_path:
        for fallback_name in ["MS Gothic", "Meiryo"]:
            f_path = get_windows_font_path(fallback_name)
            if f_path:
                break

    if f_path:
        return fitz.Font(fontfile=f_path)
    return fitz.Font(fontname="helv")
