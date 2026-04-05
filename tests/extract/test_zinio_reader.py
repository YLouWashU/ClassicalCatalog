from extract.zinio_reader import slugify


def test_slugify_basic():
    assert slugify("The Art of Fugue") == "the_art_of_fugue"


def test_slugify_special_chars():
    assert slugify("Sheku & Isata Kanneh-Mason") == "sheku_isata_kanneh_mason"


def test_slugify_apostrophe():
    assert slugify("Editor's Choice") == "editor_s_choice"
