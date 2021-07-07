import pytest
from sefaria.model.text import Ref, library
from sefaria.model.ref_part import *
from sefaria.model.abstract import AbstractMongoRecord
from sefaria.model.ref_part import RefPartType as RPT
from spacy.lang.he import Hebrew
from spacy.lang.en import English


@pytest.fixture(scope='module')
def duplicate_terms():
    initial_slug = "rashiBLAHBLAH"
    t = NonUniqueTerm({"slug": initial_slug, "titles": [{
        "text": "Rashi",
        "lang": "en",
        "primary": True
    }]})
    t.save()

    s = NonUniqueTerm({"slug": initial_slug, "titles": [{
        "text": "Rashi",
        "lang": "en",
        "primary": True
    }]})

    s.save()

    yield t, s, initial_slug

    t.delete()
    s.delete()


def create_raw_ref_data(context_tref, lang, tref, span_indexes, part_types):
    ref_resolver = RefResolver(lang)
    nlp = Hebrew() if lang == 'he' else English()
    doc = nlp(tref)
    span = doc[0:]
    part_spans = [span[index] for index in span_indexes]
    raw_ref = RawRef([RawRefPart("input", part_type, part_span) for part_type, part_span in zip(part_types, part_spans)], span)

    return ref_resolver, raw_ref, Ref(context_tref)


def test_duplicate_terms(duplicate_terms):
    t, s, initial_slug = duplicate_terms
    assert t.slug == AbstractMongoRecord.normalize_slug(initial_slug)
    assert s.slug == AbstractMongoRecord.normalize_slug(initial_slug) + "1"


@pytest.mark.parametrize(('resolver_data', 'results'), [
    [create_raw_ref_data("Rashi on Berakhot 2a", 'he', "בבלי ברכות דף ב", [0, 1, slice(2, 4)], [RPT.NAMED, RPT.NAMED, RPT.NUMBERED]), [1, ("Berakhot 2",)]],   # amud-less talmud
    [create_raw_ref_data("Rashi on Berakhot 2a", 'he', "בבלי ברכות דף ב.", [0, 1, slice(2, 5)], [RPT.NAMED, RPT.NAMED, RPT.NUMBERED]), [1, ("Berakhot 2a",)]],  # amud-ful talmud
    [create_raw_ref_data("Rashi on Berakhot 2a", 'he', "בבלי דף ב עמוד א בברכות", [0, slice(1, 5), 5], [RPT.NAMED, RPT.NUMBERED, RPT.NAMED]), [1, ("Berakhot 2a",)]]  # out of order with prefix on title
])
def test_resolver(resolver_data, results):
    ref_resolver, raw_ref, context_ref = resolver_data
    num_results, result_trefs = results
    matches = ref_resolver.get_unrefined_ref_part_matches(context_ref, raw_ref)
    refined_matches = ref_resolver.refine_ref_part_matches(matches, raw_ref)
    assert len(refined_matches) == num_results
    for result_tref, match in zip(result_trefs, refined_matches):
        assert match.ref == Ref(result_tref)