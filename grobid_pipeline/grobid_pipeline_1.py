#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pipeline:
  1. Grobid -> TEI XML
  2. Parse XML -> title (level="a" ưu tiên, fallback "m") + DOI
  3. Nếu thiếu DOI: tra Crossref theo title
  4. Với DOI -> lấy abstract (Crossref, arXiv)
  5. Nếu abstract vẫn null -> thử multiple sources (Semantic Scholar, ResearchGate, etc.)
  6. Xuất JSON
"""

import requests, xml.etree.ElementTree as ET, json, time, re, unicodedata
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
import random

UA_LIST = [
    "Academic Research Bot - Reference Pipeline v1.1 - Graduate Thesis Project (mailto:your-real-email@university.edu)",
    "Mozilla/5.0 (compatible; Academic Research; +mailto:your-real-email@university.edu) Reference Analysis",
    "Graduate Student Research Bot v1.1 - Thesis Project - Contact: your-real-email@university.edu"
]

API_UA = "Academic Research Pipeline/1.1 (Graduate Thesis Project; mailto:your-real-email@university.edu)"   # THAY EMAIL THẬT

def get_random_ua():
    return random.choice(UA_LIST)

# -------------------- GROBID -------------------- #
def extract_references_grobid(pdf_path, output_xml_path):
    url = "http://localhost:8070/api/processReferences"
    with open(pdf_path, 'rb') as f:
        r = requests.post(url, files={'input': (pdf_path, f, 'application/pdf')})
    if r.ok:
        with open(output_xml_path, 'w', encoding='utf-8') as out:
            out.write(r.text)
        print(f"✔ Đã ghi file XML: {output_xml_path}")
        return True
    print(f"❌ Lỗi Grobid {r.status_code}")
    return False


# -------------------- TIỆN ÍCH DOI & TITLE -------------------- #
def _crossref_title(doi):
    try:
        r = requests.get(f"https://api.crossref.org/works/{quote(doi)}",
                         headers={'User-Agent': API_UA}, timeout=10)
        if r.ok:
            return r.json()['message']['title'][0]
    except Exception:
        pass
    return ''


def _slug(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt).lower()
    return re.sub(r'\W+', '', txt)[:120]


def _fuzzy_match(gold, candidate, threshold=0.6):  # Giảm threshold từ 0.8 xuống 0.6
    """Kiểm tra độ tương đồng giữa 2 title đã được slug"""
    if not gold or not candidate:
        return False
    
    gold_words = set(gold.split())
    candidate_words = set(candidate.split())
    
    if not gold_words or not candidate_words:
        return False
    
    intersection = len(gold_words & candidate_words)
    union = len(gold_words | candidate_words)
    
    return (intersection / union) >= threshold if union > 0 else False


def _search_doi_by_title(title):
    """Trả về DOI nếu Crossref có bản ghi có title khớp hoàn toàn"""
    try:
        r = requests.get("https://api.crossref.org/works",
                         params={'query.title': title, 'rows': 5},
                         headers={'User-Agent': API_UA}, timeout=10)
        if not r.ok:
            return None
        gold = _slug(title)
        for item in r.json()['message']['items']:
            if item.get('title'):
                if _slug(item['title'][0]) == gold:
                    return item['DOI']
    except Exception:
        pass
    return None


# --------------- ARXIV ------------------ #
def _arxiv_title(arxiv_id):
    try:
        r = requests.get(f"https://export.arxiv.org/api/query?id_list={arxiv_id}",
                         timeout=10)
        if r.ok:
            root = ET.fromstring(r.text)
            t = root.find('.//{http://www.w3.org/2005/Atom}title')
            return (t.text or '').strip() if t is not None else ''
    except Exception:
        pass
    return ''


def _arxiv_abs(arxiv_id):
    try:
        r = requests.get(f"https://export.arxiv.org/api/query?id_list={arxiv_id}",
                         timeout=10)
        if r.ok:
            root = ET.fromstring(r.text)
            s = root.find('.//{http://www.w3.org/2005/Atom}summary')
            return (s.text or '').strip() if s is not None else None
    except Exception:
        pass
    return None


def _arxiv_abs_by_title(title):
    """Tìm abstract từ arXiv bằng title với fuzzy matching"""
    try:
        # Thử search với title đầy đủ
        r = requests.get("https://export.arxiv.org/api/query",
                         params={'search_query': f'ti:"{title}"', 'max_results': 5},
                         timeout=15)
        if r.ok:
            root = ET.fromstring(r.text)
            gold = _slug(title)
            
            for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                entry_title = entry.find('.//{http://www.w3.org/2005/Atom}title')
                if entry_title is not None:
                    entry_slug = _slug(entry_title.text)
                    if entry_slug == gold or _fuzzy_match(gold, entry_slug):
                        summary = entry.find('.//{http://www.w3.org/2005/Atom}summary')
                        if summary is not None:
                            return summary.text.strip()
        
        # Nếu không tìm thấy, thử search với keywords chính
        title_words = title.lower().split()
        key_words = [w for w in title_words if len(w) > 3][:4]
        
        if key_words:
            search_query = ' AND '.join([f'ti:{word}' for word in key_words])
            r = requests.get("https://export.arxiv.org/api/query",
                             params={'search_query': search_query, 'max_results': 3},
                             timeout=15)
            if r.ok:
                root = ET.fromstring(r.text)
                gold = _slug(title)
                
                for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                    entry_title = entry.find('.//{http://www.w3.org/2005/Atom}title')
                    if entry_title is not None and _fuzzy_match(gold, _slug(entry_title.text)):
                        summary = entry.find('.//{http://www.w3.org/2005/Atom}summary')
                        if summary is not None:
                            return summary.text.strip()
                            
    except Exception:
        pass
    return None


# --------------- CROSSREF ABSTRACT ---------------- #
def get_abstract_from_crossref(doi):
    try:
        r = requests.get(f"https://api.crossref.org/works/{quote(doi)}",
                         headers={'User-Agent': API_UA}, timeout=10)
        if r.ok:
            abs_raw = r.json()['message'].get('abstract')
            if abs_raw and 'withheld' not in abs_raw.lower():
                return re.sub(r'<[^>]+>', '', abs_raw).strip()
    except Exception:
        pass
    return None


def _search_abstract_by_title_crossref(title):
    """Tìm abstract trực tiếp bằng title từ Crossref với fuzzy matching"""
    try:
        r = requests.get("https://api.crossref.org/works",
                         params={'query.title': title, 'rows': 5},
                         headers={'User-Agent': API_UA}, timeout=10)
        if not r.ok:
            return None
        
        gold = _slug(title)
        
        # Thử khớp chính xác trước
        for item in r.json()['message']['items']:
            if item.get('title') and _slug(item['title'][0]) == gold:
                abs_raw = item.get('abstract')
                if abs_raw and 'withheld' not in abs_raw.lower():
                    return re.sub(r'<[^>]+>', '', abs_raw).strip()
        
        # Nếu không khớp chính xác, thử fuzzy matching
        for item in r.json()['message']['items']:
            if item.get('title'):
                item_slug = _slug(item['title'][0])
                if _fuzzy_match(gold, item_slug):
                    abs_raw = item.get('abstract')
                    if abs_raw and 'withheld' not in abs_raw.lower():
                        return re.sub(r'<[^>]+>', '', abs_raw).strip()
                        
    except Exception:
        pass
    return None


# --------------- SEMANTIC SCHOLAR API ---------------- #
def get_abstract_from_semantic_scholar(title, doi=None):
    """Lấy abstract từ Semantic Scholar API với enhanced debugging"""
    try:
        # Thử search bằng DOI trước nếu có
        if doi:
            print(f"        🔗 Semantic Scholar DOI: {doi}")
            r = requests.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                           params={'fields': 'abstract'},
                           headers={'User-Agent': API_UA}, timeout=15)
            
            print(f"        📡 Semantic Scholar DOI search: {r.status_code}")
            
            if r.ok:
                data = r.json()
                if data.get('abstract'):
                    print(f"        💡 DOI abstract length: {len(data['abstract'])}")
                    return data['abstract'].strip()
                else:
                    print(f"        ℹ️  DOI found but no abstract field - trying title search")
            elif r.status_code == 404:
                print(f"        ℹ️  DOI not found in Semantic Scholar")
            elif r.status_code == 429:
                print(f"        ⏰ Rate limited by Semantic Scholar - skipping title search")
                return None  # Skip title search if already rate limited
            elif r.status_code == 403:
                print(f"        🚫 BLOCKED by Semantic Scholar - IP may be banned")
                return None
            elif r.status_code >= 500:
                print(f"        🔧 Semantic Scholar server error: {r.status_code}")
            else:
                print(f"        ❌ Semantic Scholar error: {r.status_code}")
        
        # Search bằng title - only if DOI search wasn't rate limited
        print(f"        🔍 Semantic Scholar title: {title[:30]}...")
        r = requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
                         params={'query': title, 'fields': 'abstract,title', 'limit': 5},
                         headers={'User-Agent': API_UA}, timeout=15)
        
        print(f"        📡 Semantic Scholar title search: {r.status_code}")
        
        if r.ok:
            data = r.json()
            results_count = len(data.get('data', []))
            print(f"        📊 Found {results_count} results")
            
            gold = _slug(title)
            
            for i, paper in enumerate(data.get('data', [])):
                if paper.get('title') and paper.get('abstract'):
                    paper_slug = _slug(paper['title'])
                    similarity = _fuzzy_match(gold, paper_slug)
                    print(f"        🎯 Result {i+1}: {similarity} similarity")
                    
                    if paper_slug == gold or similarity:
                        print(f"        ✅ Title match found!")
                        return paper['abstract'].strip()
            
            print(f"        ❌ No matching titles found")
        elif r.status_code == 429:
            print(f"        ⏰ Rate limited by Semantic Scholar (title search)")
        elif r.status_code == 403:
            print(f"        🚫 BLOCKED by Semantic Scholar - IP may be banned")
        elif r.status_code >= 500:
            print(f"        🔧 Semantic Scholar server error: {r.status_code}")
        else:
            print(f"        ❌ Semantic Scholar title search error: {r.status_code}")
                        
    except requests.RequestException as e:
        print(f"        🌐 Network error: {str(e)[:100]}")
    except Exception as e:
        print(f"        💥 Unexpected error: {str(e)[:100]}")
    
    return None


# --------------- RESEARCHGATE SCRAPING ---------------- #
def get_abstract_from_researchgate(title):
    """Scrape abstract từ ResearchGate"""
    try:
        search_url = f"https://www.researchgate.net/search.Search.html?type=publication&query={quote(title)}"
        headers = {'User-Agent': get_random_ua()}
        
        r = requests.get(search_url, headers=headers, timeout=15)
        if not r.ok:
            return None
            
        soup = BeautifulSoup(r.text, 'html.parser')
        gold = _slug(title)
        
        # Tìm các kết quả search
        for result in soup.find_all('div', class_=['nova-legacy-c-card__body', 'nova-legacy-v-publication-item__body']):
            title_elem = result.find('a', href=re.compile(r'/publication/'))
            if title_elem:
                result_title = title_elem.get_text(strip=True)
                if result_title and (_slug(result_title) == gold or _fuzzy_match(gold, _slug(result_title))):
                    # Tìm abstract trong result này
                    abstract_elem = result.find('div', class_='nova-legacy-v-publication-item__description')
                    if abstract_elem:
                        abstract_text = abstract_elem.get_text(strip=True)
                        if len(abstract_text) > 50:  # Đảm bảo không phải snippet ngắn
                            return abstract_text
                            
    except Exception:
        pass
    return None


# --------------- GOOGLE SCHOLAR SCRAPING (FIXED) ---------------- #
def get_abstract_from_google_scholar(title):
    """Scrape abstract từ Google Scholar - cẩn thận với rate limiting"""
    try:
        search_url = f"https://scholar.google.com/scholar?q={quote(title)}"
        headers = {'User-Agent': get_random_ua()}
        
        r = requests.get(search_url, headers=headers, timeout=20)
        if not r.ok:
            print(f"        ❌ Google Scholar HTTP {r.status_code}")
            return None
            
        soup = BeautifulSoup(r.text, 'html.parser')
        gold = _slug(title)
        
        # Tìm kết quả trong Google Scholar
        for result in soup.find_all('div', class_='gs_ri'):
            title_elem = result.find('h3')
            if title_elem:
                result_title = title_elem.get_text(strip=True)
                if result_title and (_slug(result_title) == gold or _fuzzy_match(gold, _slug(result_title))):
                    # Tìm abstract/snippet
                    abstract_elem = result.find('div', class_='gs_rs')
                    if abstract_elem:
                        abstract_text = abstract_elem.get_text(strip=True)
                        if len(abstract_text) > 50:
                            return abstract_text
                            
    except Exception as e:
        print(f"        ❌ Google Scholar error: {str(e)[:50]}")
    return None


# --------------- OPENALEX API ---------------- #
def get_abstract_from_openalex(title, doi=None):
    """Lấy abstract từ OpenAlex API - free academic database"""
    try:
        # Thử search bằng DOI trước nếu có
        if doi:
            print(f"        🔗 OpenAlex DOI: {doi}")
            # OpenAlex format: https://doi.org/10.xxxx
            if not doi.startswith('http'):
                doi_url = f"https://doi.org/{doi}"
            else:
                doi_url = doi
                
            r = requests.get(f"https://api.openalex.org/works/{doi_url}",
                           headers={'User-Agent': API_UA}, timeout=15)
            
            print(f"        📡 OpenAlex DOI search: {r.status_code}")
            
            if r.ok:
                data = r.json()
                abstract = data.get('abstract_inverted_index')
                if abstract:
                    # Convert inverted index to text
                    words = [''] * (max(max(positions) for positions in abstract.values()) + 1)
                    for word, positions in abstract.items():
                        for pos in positions:
                            words[pos] = word
                    abstract_text = ' '.join(words).strip()
                    if len(abstract_text) > 50:
                        print(f"        💡 OpenAlex DOI abstract length: {len(abstract_text)}")
                        return abstract_text
                else:
                    print(f"        ℹ️  OpenAlex DOI found but no abstract")
            elif r.status_code == 404:
                print(f"        ℹ️  DOI not found in OpenAlex")
            else:
                print(f"        ❌ OpenAlex DOI error: {r.status_code}")
        
        # Search bằng title
        print(f"        🔍 OpenAlex title search: {title[:30]}...")
        r = requests.get("https://api.openalex.org/works",
                         params={'search': title, 'limit': 5},
                         headers={'User-Agent': API_UA}, timeout=15)
        
        print(f"        📡 OpenAlex title search: {r.status_code}")
        
        if r.ok:
            data = r.json()
            results_count = len(data.get('results', []))
            print(f"        📊 Found {results_count} OpenAlex results")
            
            gold = _slug(title)
            
            for i, work in enumerate(data.get('results', [])):
                work_title = work.get('title', '')
                if work_title:
                    work_slug = _slug(work_title)
                    similarity = _fuzzy_match(gold, work_slug)
                    print(f"        🎯 OpenAlex Result {i+1}: {similarity} similarity")
                    
                    if work_slug == gold or similarity:
                        abstract = work.get('abstract_inverted_index')
                        if abstract:
                            # Convert inverted index to text
                            words = [''] * (max(max(positions) for positions in abstract.values()) + 1)
                            for word, positions in abstract.items():
                                for pos in positions:
                                    words[pos] = word
                            abstract_text = ' '.join(words).strip()
                            if len(abstract_text) > 50:
                                print(f"        ✅ OpenAlex title match found!")
                                return abstract_text
            
            print(f"        ❌ No matching OpenAlex titles found")
        else:
            print(f"        ❌ OpenAlex title search error: {r.status_code}")
                        
    except Exception as e:
        print(f"        💥 OpenAlex error: {str(e)[:100]}")
    
    return None


def get_abstract_from_core(title):
    """Lấy abstract từ CORE API - open access repository"""
    try:
        print(f"        🔍 CORE search: {title[:30]}...")
        r = requests.get("https://api.core.ac.uk/v3/search/works",
                         params={'q': title, 'limit': 5},
                         headers={'User-Agent': API_UA}, timeout=15)
        
        print(f"        📡 CORE search: {r.status_code}")
        
        if r.ok:
            data = r.json()
            results_count = len(data.get('results', []))
            print(f"        📊 Found {results_count} CORE results")
            
            gold = _slug(title)
            
            for i, work in enumerate(data.get('results', [])):
                work_title = work.get('title', '')
                if work_title:
                    work_slug = _slug(work_title)
                    similarity = _fuzzy_match(gold, work_slug)
                    print(f"        🎯 CORE Result {i+1}: {similarity} similarity")
                    
                    if work_slug == gold or similarity:
                        abstract = work.get('abstract')
                        if abstract and len(abstract.strip()) > 50:
                            print(f"        ✅ CORE match found!")
                            return abstract.strip()
            
            print(f"        ❌ No matching CORE results")
        else:
            print(f"        ❌ CORE error: {r.status_code}")
                        
    except Exception as e:
        print(f"        💥 CORE error: {str(e)[:100]}")
    
    return None


# --------------- UNIFIED ABSTRACT RETRIEVAL (UPDATED) ---------------- #
def get_abstract_by_title(title, doi=None):
    """Lấy abstract bằng title - optimized order và better error handling"""
    if not title or title == "No title":
        return None
    
    print(f"      🔍 Searching abstract for: {title[:50]}...")
    
    # Reordered sources - fast and reliable first
    sources = [
        ("OpenAlex", lambda: get_abstract_from_openalex(title, doi), 0.5),
        ("Crossref", lambda: _search_abstract_by_title_crossref(title), 0.3),
        ("arXiv", lambda: _arxiv_abs_by_title(title), 1),
        ("CORE", lambda: get_abstract_from_core(title), 1),
        ("Semantic Scholar", lambda: get_abstract_from_semantic_scholar(title, doi), 2),
        ("Google Scholar", lambda: get_abstract_from_google_scholar(title), 8),
        ("ResearchGate", lambda: get_abstract_from_researchgate(title), 4)
    ]
    
    for source_name, source_func, delay in sources:
        try:
            print(f"        📡 Trying {source_name}...")
            abstract = source_func()
            if abstract and len(abstract.strip()) > 30:
                print(f"        ✅ Found from {source_name}")
                return abstract.strip()
            
            print(f"        ⏱️  Waiting {delay}s...")
            time.sleep(delay)
            
        except Exception as e:
            print(f"        ❌ {source_name} failed: {str(e)[:50]}")
            # Still wait on network errors to avoid hammering
            time.sleep(delay * 0.5)
            continue
    
    return None


# --------------- PARSER ------------------ #
def parse_grobid_xml(xml_path):
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    root = ET.parse(xml_path).getroot()

    bib_entries, citation_candidates = {}, []

    for bibl in root.findall('.//tei:biblStruct', ns):
        bid = bibl.get('{http://www.w3.org/XML/1998/namespace}id')
        if not bid:
            continue

        # --- title ---
        t_a = bibl.find('.//tei:title[@level="a"]', ns)
        if t_a is not None:
            title = ''.join(t_a.itertext()).strip()
        else:
            t_m = bibl.find('.//tei:title[@level="m"]', ns)
            title = ''.join(t_m.itertext()).strip() if t_m is not None else "No title"

        # --- doi ---
        doi_elem = bibl.find('.//tei:idno[@type="DOI"]', ns)
        doi = None
        if doi_elem is not None and doi_elem.text:
            m = re.search(r'10\.\d+/.+', doi_elem.text.strip())
            if m:
                doi = m.group(0)

        # fallback title (arXiv / Crossref)
        if not title and doi and 'arxiv' in doi.lower():
            arxiv_match = re.search(r'arxiv[\.:/]?(\d+\.\d+)', doi.lower())
            if arxiv_match:
                title = _arxiv_title(arxiv_match.group(1))
        if not title and doi:
            title = _crossref_title(doi)
        if not title:
            title = "No title"

        bib_entries[bid] = {"title": title, "doi": doi, "abstract": None}
        citation_candidates.append(bid)

    return bib_entries, citation_candidates


# --------------- ENRICH ------------------ #
def enrich_entries(bib_entries):
    print("🔍 Bổ sung DOI và abstract từ multiple sources...")
    
    total_entries = len(bib_entries)
    doi_added = 0
    abs_from_doi = 0
    abs_from_title = 0
    failed_entries = []
    
    for i, (bid, entry) in enumerate(bib_entries.items(), 1):
        doi, title = entry['doi'], entry['title']
        print(f"  [{i}/{total_entries}] Processing: {bid}")

        # --- (1) Nếu CHƯA có DOI nhưng có title → tra Crossref ---
        if not doi and title != "No title":
            doi_found = _search_doi_by_title(title)
            if doi_found:
                entry['doi'] = doi = doi_found
                doi_added += 1
                print(f"    ✔ Found DOI by title: {doi}")

        # --- (2) Lấy abstract bằng DOI ---
        if doi:
            abs_text = get_abstract_from_crossref(doi)
            if not abs_text and 'arxiv' in doi.lower():
                arxiv_match = re.search(r'arxiv[\.:/]?(\d+\.\d+)', doi.lower())
                if arxiv_match:
                    abs_text = _arxiv_abs(arxiv_match.group(1))
            
            if abs_text:
                entry['abstract'] = abs_text
                abs_from_doi += 1
                print(f"    ✔ Got abstract from DOI")

        # --- (3) Nếu vẫn chưa có abstract → thử multiple sources ---
        if not entry['abstract'] and title != "No title":
            abs_text = get_abstract_by_title(title, doi)
            if abs_text:
                entry['abstract'] = abs_text
                abs_from_title += 1
                print(f"    ✔ Got abstract from title search")
            else:
                failed_entries.append((bid, title[:50] + "..." if len(title) > 50 else title))
                print(f"    ❌ No abstract found")

        # Progressive delay - tăng dần để tránh rate limit
        delay = min(1.5 + (i * 0.1), 3.0)  # Start 1.5s, max 3s
        time.sleep(delay)

    print(f"\n📈 Final Summary:")
    print(f"   DOI added by title search: {doi_added}")
    print(f"   Abstracts from DOI: {abs_from_doi}")
    print(f"   Abstracts from title search: {abs_from_title}")
    print(f"   Total abstracts: {abs_from_doi + abs_from_title}")
    print(f"   Success rate: {(abs_from_doi + abs_from_title)/total_entries*100:.1f}%")
    print(f"   Failed entries: {len(failed_entries)}")
    
    if failed_entries:
        print(f"\n❌ Entries without abstract:")
        for bid, title in failed_entries[:5]:
            print(f"   {bid}: {title}")
        if len(failed_entries) > 5:
            print(f"   ... and {len(failed_entries) - 5} more")


# --------------- OUTPUT ------------------ #
def create_output_structure(text_stub, bib_entries, citation_candidates):
    return {
        "text": text_stub or ["Sample text content"],
        "citation_candidates": citation_candidates,
        "bib_entries": bib_entries
    }


def save_json_output(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✔ JSON saved → {path}")


# --------------- MAIN -------------------- #
def main():
    pdf_path = "paper.pdf"
    xml_path = "references_grobid.xml"
    output = "references_with_abstracts.json"
    
    # Bước 1: Grobid extraction
    print("🔄 Step 1: Extracting references with Grobid...")
    if not extract_references_grobid(pdf_path, xml_path):
        print("❌ Grobid extraction failed. Exiting.")
        return
    
    # Bước 2: Parse XML
    print("🔄 Step 2: Parsing Grobid XML...")
    try:
        bib_entries, citation_candidates = parse_grobid_xml(xml_path)
        print(f"✔ Parsed {len(bib_entries)} bibliography entries")
        print(f"✔ Found {len(citation_candidates)} citation candidates")
    except Exception as e:
        print(f"❌ XML parsing failed: {e}")
        return
    
    if not bib_entries:
        print("❌ No bibliography entries found. Exiting.")
        return
    
    # Bước 3: Enrich với DOI và abstracts
    print("🔄 Step 3: Enriching entries with DOI and abstracts...")
    try:
        enrich_entries(bib_entries)
    except Exception as e:
        print(f"❌ Enrichment failed: {e}")
        return
    
    # Bước 4: Tạo output structure
    print("🔄 Step 4: Creating output structure...")
    text_stub = ["This is extracted text content from the PDF document."]
    output_data = create_output_structure(text_stub, bib_entries, citation_candidates)
    
    # Bước 5: Save JSON
    print("🔄 Step 5: Saving results...")
    try:
        save_json_output(output_data, output)
        print(f"✅ Pipeline completed successfully!")
        print(f"📄 Output file: {output}")
        
        # Statistics summary
        total_entries = len(bib_entries)
        entries_with_doi = sum(1 for e in bib_entries.values() if e['doi'])
        entries_with_abstract = sum(1 for e in bib_entries.values() if e['abstract'])
        
        print(f"\n📊 Final Statistics:")
        print(f"   Total entries: {total_entries}")
        print(f"   Entries with DOI: {entries_with_doi} ({entries_with_doi/total_entries*100:.1f}%)")
        print(f"   Entries with abstract: {entries_with_abstract} ({entries_with_abstract/total_entries*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Failed to save output: {e}")
        return


if __name__ == "__main__":
    print("🚀 Academic Reference Pipeline v1.1")
    print("=" * 50)
    main()