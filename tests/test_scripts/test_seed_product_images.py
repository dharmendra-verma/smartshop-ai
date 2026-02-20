from scripts.seed_product_images import _image_url_for


def test_image_url_for_deterministic():
    url1 = _image_url_for("SP0001")
    url2 = _image_url_for("SP0001")
    assert url1 == url2
    assert "picsum.photos" in url1
    assert "/400/300" in url1


def test_image_url_for_different_products_different_urls():
    assert _image_url_for("SP0001") != _image_url_for("SP0099")
