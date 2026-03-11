from __future__ import annotations

import pytest

from citation_check.grobid import check_grobid, extract_references, parse_tei_references

SAMPLE_TEI_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text>
    <body/>
    <back>
      <listBibl>
        <biblStruct>
          <analytic>
            <title level="a">Attention Is All You Need</title>
            <author>
              <persName>
                <forename>Ashish</forename>
                <surname>Vaswani</surname>
              </persName>
            </author>
            <author>
              <persName>
                <forename>Noam</forename>
                <surname>Shazeer</surname>
              </persName>
            </author>
            <idno type="DOI">10.48550/arXiv.1706.03762</idno>
          </analytic>
          <monogr>
            <title level="m">Advances in Neural Information Processing Systems</title>
            <imprint>
              <date when="2017">2017</date>
            </imprint>
          </monogr>
        </biblStruct>
        <biblStruct>
          <analytic>
            <title level="a">BERT: Pre-training of Deep Bidirectional Transformers</title>
            <author>
              <persName>
                <forename>Jacob</forename>
                <surname>Devlin</surname>
              </persName>
            </author>
          </analytic>
          <monogr>
            <title level="j">arXiv preprint</title>
            <imprint>
              <date when="2018">2018</date>
            </imprint>
          </monogr>
        </biblStruct>
      </listBibl>
    </back>
  </text>
</TEI>
"""

MINIMAL_TEI_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text>
    <body/>
    <back>
      <listBibl>
        <biblStruct>
          <monogr>
            <title level="m">A Book Title</title>
            <imprint/>
          </monogr>
        </biblStruct>
      </listBibl>
    </back>
  </text>
</TEI>
"""

EMPTY_TEI_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text>
    <body/>
    <back>
      <listBibl/>
    </back>
  </text>
</TEI>
"""


class TestParseTeiReferences:
    def test_parses_two_references(self):
        refs = parse_tei_references(SAMPLE_TEI_XML)
        assert len(refs) == 2

    def test_first_reference_fields(self):
        refs = parse_tei_references(SAMPLE_TEI_XML)
        ref = refs[0]
        assert ref.title == "Attention Is All You Need"
        assert ref.authors == ["Ashish Vaswani", "Noam Shazeer"]
        assert ref.year == 2017
        assert ref.venue == "Advances in Neural Information Processing Systems"
        assert ref.doi == "10.48550/arXiv.1706.03762"
        assert ref.index == 0

    def test_second_reference_journal_venue(self):
        refs = parse_tei_references(SAMPLE_TEI_XML)
        ref = refs[1]
        assert ref.title == "BERT: Pre-training of Deep Bidirectional Transformers"
        assert ref.authors == ["Jacob Devlin"]
        assert ref.year == 2018
        assert ref.venue == "arXiv preprint"
        assert ref.index == 1

    def test_monograph_only(self):
        refs = parse_tei_references(MINIMAL_TEI_XML)
        assert len(refs) == 1
        ref = refs[0]
        assert ref.title == "A Book Title"
        assert ref.authors == []
        assert ref.year is None
        assert ref.venue is None
        assert ref.doi is None

    def test_empty_bibliography(self):
        refs = parse_tei_references(EMPTY_TEI_XML)
        assert refs == []

    def test_raw_text_populated(self):
        refs = parse_tei_references(SAMPLE_TEI_XML)
        assert len(refs[0].raw_text) > 0


class TestCheckGrobid:
    @pytest.mark.anyio
    async def test_healthy(self, httpx_mock):
        httpx_mock.add_response(url="http://localhost:8070/api/isalive", status_code=200)
        result = await check_grobid()
        assert result is True

    @pytest.mark.anyio
    async def test_unhealthy(self, httpx_mock):
        httpx_mock.add_response(url="http://localhost:8070/api/isalive", status_code=503)
        result = await check_grobid()
        assert result is False


class TestExtractReferences:
    @pytest.mark.anyio
    async def test_extract(self, httpx_mock, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        httpx_mock.add_response(
            url="http://localhost:8070/api/processReferences",
            text=SAMPLE_TEI_XML,
        )

        refs = await extract_references(str(pdf_file))
        assert len(refs) == 2
        assert refs[0].title == "Attention Is All You Need"
