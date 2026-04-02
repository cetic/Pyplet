"""Unit tests for pyplet DOM components."""

# import json

from htpy import a  # , audio, div, img, input, label, video

from pyplet.shared.dom import (
    browser,
    checkbox,
    download,
    image,
    pp_audio,
    pp_button,
    pp_video,
    radio,
    slider,
    upload,
    upload_area,
)


class TestDownload:
    def test_download_from_server(self):
        result = download("file.txt", "Download File")
        expected = a(
            ".btn-primary.btn",
            href="file.txt",
            text="Download File",
            download=True,
        )["Download File"]
        assert str(result) == str(expected)

    def test_download_from_vfs(self):
        result = download("file.txt", "Download File", from_vfs=True)
        expected = a(
            ".btn-primary.btn",
            href="#",
            text="Download File",
            onclick="event.preventDefault(); download_vfs_file('file.txt');",
        )["Download File"]
        assert str(result) == str(expected)

    def test_download_custom_extra_classes(self):
        result = download("file.txt", extra_classes=".w-100")
        assert 'class="btn-primary btn w-100"' in str(result)

    def test_download_overwrite_classes(self):
        result = download("file.txt", overwrite_classes=".custom-btn")
        assert 'class="custom-btn"' in str(result)
        assert "btn-primary" not in str(result)

    def test_download_additional_attrs(self):
        result = download("file.txt", id="my-btn")
        assert 'id="my-btn"' in str(result)


class TestUpload:
    def test_upload_basic(self):
        result = upload()
        html = str(result)
        assert "btn-primary btn" in html
        assert "upload_file" in html
        assert 'href="#"' in html

    def test_upload_with_destination(self):
        result = upload(client_destination="/uploads")
        html = str(result)
        assert "/uploads" in html

    def test_upload_with_filename(self):
        result = upload(filename="my_file.csv")
        html = str(result)
        assert "my_file.csv" in html

    def test_upload_with_extensions(self):
        result = upload(allowed_extensions=["jpg", "png"])
        html = str(result)
        assert "jpg" in html
        assert "png" in html

    def test_upload_wildcard_extensions_cleared(self):
        result_wildcard = upload(allowed_extensions=["*"])
        result_none = upload(allowed_extensions=None)
        assert str(result_wildcard) == str(result_none)

    def test_upload_custom_classes(self):
        result = upload(overwrite_classes=".my-btn")
        assert 'class="my-btn"' in str(result)


class TestUploadArea:
    def test_upload_area_basic(self):
        result = upload_area()
        html = str(result)
        assert "upload-area" in html
        assert "handle_drop" in html
        assert "handle_click" in html
        assert "drag-over" in html

    def test_upload_area_with_destination(self):
        result = upload_area(client_destination="/uploads")
        html = str(result)
        assert "/uploads" in html

    def test_upload_area_wildcard_extensions_cleared(self):
        result_wildcard = upload_area(allowed_extensions=["*"])
        result_none = upload_area(allowed_extensions=None)
        assert str(result_wildcard) == str(result_none)

    def test_upload_area_size_limits_in_js(self):
        result = upload_area(total_size_limit=1024, per_file_size_limit=512)
        html = str(result)
        assert "1024" in html
        assert "512" in html


class TestImage:
    def test_image_from_server(self):
        result = image("photo.jpg")
        html = str(result)
        assert "<img" in html
        assert 'src="photo.jpg"' in html

    def test_image_from_vfs(self):
        result = image("photo.jpg", from_vfs=True)
        html = str(result)
        assert "<img" in html
        assert 'data-vfs-src="photo.jpg"' in html

    def test_image_additional_attrs(self):
        result = image("photo.jpg", alt="A photo", width="200")
        html = str(result)
        assert 'alt="A photo"' in html
        assert 'width="200"' in html


class TestVideo:
    def test_video_from_server(self):
        result = pp_video("clip.mp4")
        html = str(result)
        assert "<video" in html
        assert 'src="clip.mp4"' in html
        assert "controls" in html

    def test_video_from_vfs(self):
        result = pp_video("clip.mp4", from_vfs=True)
        html = str(result)
        assert "<video" in html
        assert 'data-vfs-src="clip.mp4"' in html


class TestAudio:
    def test_audio_from_server(self):
        result = pp_audio("song.mp3")
        html = str(result)
        assert "<audio" in html
        assert 'src="song.mp3"' in html
        assert "controls" in html

    def test_audio_from_vfs(self):
        result = pp_audio("song.mp3", from_vfs=True)
        html = str(result)
        assert "<audio" in html
        assert 'data-vfs-src="song.mp3"' in html


class TestSlider:
    def test_slider_defaults(self):
        result = slider()
        html = str(result)
        assert "<input" in html
        assert 'type="range"' in html
        assert "form-range" in html

    def test_slider_custom_range(self):
        result = slider(value=25, min=0, max=50, step=5)
        html = str(result)
        assert 'value="25"' in html
        assert 'min="0"' in html
        assert 'max="50"' in html
        assert 'step="5"' in html

    def test_slider_with_id(self):
        result = slider(id="my-slider")
        html = str(result)
        assert 'id="my-slider"' in html

    def test_slider_extra_classes(self):
        result = slider(extra_classes=".w-100")
        assert "w-100" in str(result)


class TestRadio:
    def test_radio_renders_options(self):
        result = radio(["yes", "no", "maybe"])
        html = str(result)
        assert "yes" in html
        assert "no" in html
        assert "maybe" in html
        assert 'type="radio"' in html

    def test_radio_selected(self):
        result = radio(["a", "b", "c"], selected="b")
        html = str(result)
        assert "checked" in html
        # Only one checked
        assert html.count("checked") == 1

    def test_radio_name_attribute(self):
        result = radio(["x", "y"], name="my_group")
        html = str(result)
        assert 'name="my_group"' in html

    def test_radio_empty_options(self):
        result = radio([])
        html = str(result)
        assert 'type="radio"' not in html


class TestCheckbox:
    def test_checkbox_unchecked(self):
        result = checkbox("Accept terms")
        html = str(result)
        assert "<input" in html
        assert 'type="checkbox"' in html
        assert "checked" not in html
        assert "Accept terms" in html

    def test_checkbox_checked(self):
        result = checkbox("Yes", checked=True)
        html = str(result)
        assert "checked" in html

    def test_checkbox_with_id(self):
        result = checkbox("Label", id="my-check")
        html = str(result)
        assert 'id="my-check"' in html
        assert 'for="my-check"' in html

    def test_checkbox_default_id(self):
        result = checkbox("Label")
        html = str(result)
        assert 'id="checkbox"' in html


class TestPpButton:
    def test_button_default(self):
        result = pp_button("Click me")
        html = str(result)
        assert "<button" in html
        assert "Click me" in html
        assert "btn-primary" in html

    def test_button_variant(self):
        result = pp_button("Delete", variant="danger")
        html = str(result)
        assert "btn-danger" in html

    def test_button_with_id(self):
        result = pp_button("Submit", id="submit-btn")
        html = str(result)
        assert 'id="submit-btn"' in html

    def test_button_extra_classes(self):
        result = pp_button("Go", extra_classes=".w-100")
        assert "w-100" in str(result)


class TestBrowser:
    def test_browser_renders_div(self):
        result = browser()
        html = str(result)
        assert "<div" in html
        assert "file-browser" in html

    def test_browser_root_path(self):
        result = browser(root_path="/data")
        html = str(result)
        assert "/data" in html

    def test_browser_with_id(self):
        result = browser(id="my-browser")
        html = str(result)
        assert 'id="my-browser"' in html


class TestMergeClasses:
    def test_default_only(self):
        from pyplet.shared.dom._dom import _merge_classes

        assert _merge_classes(".btn") == ".btn"

    def test_extra_classes_added(self):
        from pyplet.shared.dom._dom import _merge_classes

        assert _merge_classes(".btn", extra_classes=".w-100") == ".btn.w-100"

    def test_extra_classes_auto_prefixed(self):
        from pyplet.shared.dom._dom import _merge_classes

        assert _merge_classes(".btn", extra_classes="w-100") == ".btn.w-100"

    def test_overwrite_classes_replaces(self):
        from pyplet.shared.dom._dom import _merge_classes

        assert _merge_classes(".btn", overwrite_classes=".custom") == ".custom"

    def test_overwrite_takes_precedence_over_extra(self):
        from pyplet.shared.dom._dom import _merge_classes

        result = _merge_classes(
            ".btn", extra_classes=".x", overwrite_classes=".y"
        )
        assert result == ".y"
