from edgar_screener.fetch import classify, index_url, parse_master

MASTER = """Description:           Daily Index of EDGAR Dissemination Feed by Form Type
Last Data Received:    Jun 2, 2025
Comments:              webmaster@sec.gov
Anonymous FTP:         ftp://ftp.sec.gov/edgar/

CIK|Company Name|Form Type|Date Filed|File Name
--------------------------------------------------------------------------------
1000623|Mativ Holdings, Inc.|4|20250602|edgar/data/1000623/0001562180-25-004291.txt
1318605|Tesla, Inc.|8-K|20250602|edgar/data/1318605/0001318605-25-000123.txt
789019|MICROSOFT CORP|424B5|20250602|edgar/data/789019/0000789019-25-000045.txt
garbage_line_without_pipes
999|Missing Path Co|10-Q|20250602
"""


def test_classify_buckets():
    assert classify("4") == "insider"
    assert classify("4/A") == "insider"
    assert classify("8-K") == "event"
    assert classify("SC 13D") == "stake"
    assert classify("SC 13G/A") == "stake"
    assert classify("S-1") == "offering"
    assert classify("424B5") == "offering"   # prefix match
    assert classify("424B2") == "offering"
    assert classify("10-K") == "periodic"
    assert classify("3") == "other"


def test_parse_master_extracts_valid_rows_only():
    rows = parse_master(MASTER)
    assert len(rows) == 3          # 2 malformed lines skipped
    first = rows[0]
    assert first["cik"] == 1000623
    assert first["company"] == "Mativ Holdings, Inc."
    assert first["form"] == "4"
    assert first["bucket"] == "insider"
    assert first["filed_date"] == "2025-06-02"
    assert first["accession"] == "0001562180-25-004291"
    assert first["path"] == "edgar/data/1000623/0001562180-25-004291.txt"


def test_parse_master_classifies_each_row():
    buckets = [r["bucket"] for r in parse_master(MASTER)]
    assert buckets == ["insider", "event", "offering"]


def test_index_url_computes_quarter():
    assert index_url("2025-06-02").endswith("/2025/QTR2/master.20250602.idx")
    assert index_url("2025-01-15").endswith("/2025/QTR1/master.20250115.idx")
    assert index_url("2025-12-31").endswith("/2025/QTR4/master.20251231.idx")
