"""
Generate a detailed PDF solution document for the Aztec Merkle Tree interview challenge.
Uses ReportLab for pure-Python PDF generation (no LaTeX installation required).
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white, lightgrey
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Preformatted, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.lib import colors

# ── Colour palette ────────────────────────────────────────────────────────────
AZTEC_PURPLE = HexColor("#6414C8")
DARK_BG      = HexColor("#1e1e2e")
CODE_BG      = HexColor("#f5f5f5")
CODE_FG      = HexColor("#1a1a2e")
HEADER_BG    = HexColor("#ede9f7")
PASS_GREEN   = HexColor("#2e7d32")
TABLE_HEADER = HexColor("#7c3aed")

OUTPUT_PATH = "/home/user/aztec-interview-tests/eng-sessions/solution.pdf"

# ─────────────────────────────────────────────────────────────────────────────
# Page layout with header/footer
# ─────────────────────────────────────────────────────────────────────────────

def make_page_template(doc):
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id='normal')

    def on_page(canvas, doc):
        canvas.saveState()
        # Header bar
        canvas.setFillColor(AZTEC_PURPLE)
        canvas.rect(doc.leftMargin - 0.5*cm, A4[1] - 2.0*cm,
                    doc.width + 1*cm, 0.6*cm, fill=1, stroke=0)
        canvas.setFillColor(white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(doc.leftMargin, A4[1] - 1.7*cm,
                          "Aztec Engineering Interview — Merkle Tree Solution")
        canvas.drawRightString(A4[0] - doc.rightMargin, A4[1] - 1.7*cm,
                               "eng-sessions")
        # Footer
        canvas.setFillColor(colors.grey)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(A4[0] / 2, 1.2*cm, f"Page {doc.page}")
        canvas.restoreState()

    return PageTemplate(id='main', frames=[frame], onPage=on_page)


# ─────────────────────────────────────────────────────────────────────────────
# Styles
# ─────────────────────────────────────────────────────────────────────────────

BASE = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=BASE["Heading1"],
                    textColor=AZTEC_PURPLE, fontSize=18, spaceAfter=8,
                    spaceBefore=20, fontName="Helvetica-Bold")
H2 = ParagraphStyle("H2", parent=BASE["Heading2"],
                    textColor=AZTEC_PURPLE, fontSize=14, spaceAfter=6,
                    spaceBefore=14, fontName="Helvetica-Bold")
H3 = ParagraphStyle("H3", parent=BASE["Heading3"],
                    textColor=HexColor("#4a148c"), fontSize=12, spaceAfter=4,
                    spaceBefore=10, fontName="Helvetica-Bold")
BODY = ParagraphStyle("Body", parent=BASE["Normal"],
                      fontSize=10.5, leading=15, spaceAfter=6,
                      alignment=TA_JUSTIFY)
BULLET = ParagraphStyle("Bullet", parent=BODY,
                        leftIndent=18, firstLineIndent=-10, spaceAfter=4,
                        bulletIndent=4)
CODE = ParagraphStyle("Code", parent=BASE["Code"],
                      fontName="Courier", fontSize=8.5, leading=12,
                      leftIndent=12, rightIndent=12,
                      backColor=CODE_BG, spaceAfter=8, spaceBefore=4,
                      borderColor=HexColor("#cccccc"), borderWidth=0.5,
                      borderPadding=6)
MATH = ParagraphStyle("Math", parent=BODY,
                      fontName="Courier-Bold", fontSize=10,
                      leftIndent=24, backColor=HexColor("#f0eafb"),
                      borderColor=AZTEC_PURPLE, borderWidth=0.5,
                      borderPadding=6, spaceAfter=8, spaceBefore=4)
CAPTION = ParagraphStyle("Caption", parent=BASE["Normal"],
                         fontSize=9, textColor=colors.grey,
                         alignment=TA_CENTER, spaceAfter=6)
TITLE_STYLE = ParagraphStyle("Title", parent=BASE["Title"],
                              textColor=AZTEC_PURPLE, fontSize=26,
                              alignment=TA_CENTER, fontName="Helvetica-Bold",
                              spaceAfter=4)
SUBTITLE = ParagraphStyle("Subtitle", parent=BASE["Normal"],
                           fontSize=13, alignment=TA_CENTER,
                           textColor=HexColor("#555555"), spaceAfter=16)

# ─────────────────────────────────────────────────────────────────────────────
# Helper builders
# ─────────────────────────────────────────────────────────────────────────────

def hr(color=AZTEC_PURPLE, thickness=1.5):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceAfter=6, spaceBefore=6)

def b(txt):
    """Bold inline."""
    return f"<b>{txt}</b>"

def tt(txt):
    """Monospace inline."""
    return f"<font name='Courier'>{txt}</font>"

def bullet(txt):
    return Paragraph(f"\u2022\u2002{txt}", BULLET)

def code_block(src, caption=""):
    items = [Preformatted(src.strip(), CODE)]
    if caption:
        items.append(Paragraph(caption, CAPTION))
    return items

def math_block(txt):
    return Paragraph(txt, MATH)

def section_table(headers, rows, col_widths=None):
    data = [headers] + rows
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER),
        ('TEXTCOLOR',  (0, 0), (-1, 0), white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING',    (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor("#fafafa")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor("#f0eafb")]),
        ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 1), (-1, -1), 9.5),
        ('GRID', (0, 0), (-1, -1), 0.4, HexColor("#cccccc")),
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING',  (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ])
    tbl.setStyle(style)
    return tbl


# ─────────────────────────────────────────────────────────────────────────────
# Document content
# ─────────────────────────────────────────────────────────────────────────────

def build_story():
    s = []

    # ── Title page ────────────────────────────────────────────────────────────
    s.append(Spacer(1, 1.5*cm))
    s.append(hr(thickness=3))
    s.append(Paragraph("Merkle Tree Implementation", TITLE_STYLE))
    s.append(Paragraph("Aztec Engineering Interview — Full Solution Document", SUBTITLE))
    s.append(hr(thickness=3))
    s.append(Spacer(1, 0.5*cm))

    info_data = [
        ["Challenge", "eng-sessions / merkle-tree (TypeScript + C++)"],
        ["Depth",     "Configurable, default 32  (2³² ≈ 4.3 billion leaves)"],
        ["Hash",      "SHA-256  (compress: H(left ‖ right),  hash: H(data))"],
        ["Status",    "✓  All 4 TypeScript tests + 4 C++ tests passing"],
    ]
    info_tbl = Table(info_data, colWidths=[3.5*cm, 13*cm])
    info_tbl.setStyle(TableStyle([
        ('FONTNAME',  (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME',  (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE',  (0, 0), (-1, -1), 10),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.3, HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [white, HexColor("#f5f0fe")]),
    ]))
    s.append(info_tbl)
    s.append(PageBreak())

    # ── 1. Problem Overview ───────────────────────────────────────────────────
    s.append(Paragraph("1. Problem Overview", H1))
    s.append(Paragraph(
        "The challenge asks you to implement a <b>sparse binary Merkle tree</b> "
        "of configurable depth, backed by a persistent key–value store. "
        "Two identical specifications are provided:", BODY))
    s += [
        bullet(tt("eng-sessions/merkle-tree/") + "  —  TypeScript, using LevelUp / memdown (in-memory)."),
        bullet(tt("eng-sessions/merkle-tree-cpp/") + "  —  C++20, using a mock " + tt("unordered_map") + " database."),
    ]
    s.append(Spacer(1, 0.3*cm))
    s.append(Paragraph("Both require the same three operations:", BODY))

    op_tbl = section_table(
        [Paragraph(b("Method"), BODY), Paragraph(b("TypeScript"), BODY), Paragraph(b("C++"), BODY)],
        [
            ["Constructor init",    tt("constructor(...)"),          tt("MerkleTree(...)")],
            ["Membership proof",    tt("getHashPath(index)"),        tt("get_hash_path(index)")],
            ["Leaf update",         tt("updateElement(index,value)"),tt("update_element(index,value)")],
        ],
        col_widths=[5*cm, 6.5*cm, 6*cm],
    )
    s.append(op_tbl)

    # ── 2. Mathematical Background ────────────────────────────────────────────
    s.append(Paragraph("2. Mathematical Background", H1))

    s.append(Paragraph("2.1  Binary Merkle Trees", H2))
    s.append(Paragraph(
        "A <b>binary Merkle tree</b> of depth <i>d</i> is a complete binary tree "
        "with 2<super>d</super> leaves, using SHA-256 as the hash function "
        "H : {0,1}* → {0,1}²⁵⁶.", BODY))
    s += [
        bullet(b("Leaf nodes") + " (level 0): raw data v_i (64 bytes) → leaf hash ℓ_i = H(v_i)."),
        bullet(b("Internal nodes") + " (levels 1…d): n_(k,p) = H( n_(k-1, 2p) ‖ n_(k-1, 2p+1) )."),
        bullet(b("Root") + ": n_(d, 0)  —  a single 32-byte commitment to all leaf data."),
    ]

    s.append(Paragraph("2.2  Tree Geometry and Bit Arithmetic", H2))
    s.append(Paragraph(
        "Given leaf index <i>i</i> and depth <i>d</i>:", BODY))
    geo = (
        "Position at level k :  p_k(i) = floor( i / 2^k ) = i >> k\n"
        "Left-child of pair  :  p_k(i)  &  ~1   (round down to even)\n"
        "Right-child of pair :  p_k(i)  |   1   (round up to odd)\n"
        "Sibling position    :  p_k(i)  ^   1   (XOR with 1)"
    )
    s += code_block(geo)

    s.append(Paragraph("2.3  Zero Hashes for Sparse Trees", H2))
    s.append(Paragraph(
        "With depth 32, most of the 4 billion leaf slots are never written. "
        "Rather than storing empty nodes, we pre-compute a canonical "
        "<b>zero hash</b> at each level:", BODY))
    s += code_block(
        "z_0 = H( 0x00 * 64 )              // SHA-256 of 64 zero bytes\n"
        "z_k = H( z_{k-1} || z_{k-1} )    // for k = 1 … d\n\n"
        "Empty root (d=32):\n"
        "  1c9a7e5ff1cf48b4ad1582d3f4e4a1004f3b20d8c5a2b71387a4254ad933ebc5"
    )
    s.append(Paragraph(
        "Any absent node at level <i>k</i> is treated as z_k without storing it — "
        "this keeps storage O(N·d) for N inserted leaves.", BODY))

    s.append(Paragraph("2.4  Hash Paths (Merkle Proofs)", H2))
    s.append(Paragraph(
        "For leaf index <i>i</i> in a depth-<i>d</i> tree, the <b>hash path</b> "
        "Π_i is an ordered sequence of <i>d</i> sibling pairs, one per level "
        "from the leaf upward:", BODY))
    s += code_block(
        "Π_i  =  [ (n_{0, p&~1}, n_{0, p|1}),\n"
        "          (n_{1, p&~1}, n_{1, p|1}),\n"
        "          ...\n"
        "          (n_{d-1, p&~1}, n_{d-1, p|1}) ]\n"
        "where p = i >> k  at level k."
    )
    s.append(Paragraph(
        b("Verification property:") + "  Given Π_i, value v_i, and depth d, "
        "recompute c ← H(v_i); for each level-k pair (L_k, R_k) in Π_i set "
        "c ← H(L_k ‖ R_k); accept iff c = root.  "
        "This is exactly what Aztec's SNARK circuits verify in zero-knowledge.", BODY))

    s.append(Paragraph("2.5  Worked Example: Depth-2 Tree, 4 Leaves", H2))
    s.append(Paragraph(
        "Let v_i be a 64-byte buffer with i encoded in the first 4 bytes "
        "(little-endian). After inserting v_0 … v_3 into a depth-2 tree:", BODY))
    s += code_block(
        "e00 = H(v0),  e01 = H(v1),  e02 = H(v2),  e03 = H(v3)\n"
        "e10 = H(e00 || e01),   e11 = H(e02 || e03)\n"
        "root = H(e10 || e11)\n\n"
        "Expected root:\n"
        "  e645e6b5445483a358c4d15c1923c616a0e6884906b05c196d341ece93b2de42\n\n"
        "Hash paths:\n"
        "  index 0, 1  →  [ (e00, e01), (e10, e11) ]\n"
        "  index 2, 3  →  [ (e02, e03), (e10, e11) ]"
    )
    s.append(Paragraph(
        "Indices 0 and 1 share the same level-0 pair because they occupy "
        "the same two-leaf group — this is by design, as the hash path always "
        "returns the complete sibling pair at every level.", BODY))

    # ── 3. Algorithm Design ───────────────────────────────────────────────────
    s.append(Paragraph("3. Algorithm Design", H1))

    s.append(Paragraph("3.1  updateElement — Leaf Update", H2))
    s.append(Paragraph("The algorithm walks from leaf to root in a single loop:", BODY))
    s += code_block(
        "updateElement(index, value):\n"
        "  c   ← H(value)        // leaf hash\n"
        "  pos ← index\n"
        "  batch ← []\n\n"
        "  for level = 0 to depth-1:\n"
        "    batch.add( key(level, pos) → c )   // store this node\n"
        "    sibling ← getNode(level, pos ^ 1)  // DB or zero_hash[level]\n"
        "    if pos is even:\n"
        "      c ← H(c || sibling)              // c is left child\n"
        "    else:\n"
        "      c ← H(sibling || c)              // c is right child\n"
        "    pos ← pos >> 1\n\n"
        "  root ← c\n"
        "  batch.add( metadata key → root )\n"
        "  commit batch\n"
        "  return root\n\n"
        "Complexity: O(d) hash calls + O(d) DB reads + O(d) DB writes"
    )

    s.append(Paragraph("3.2  getHashPath — Membership Proof", H2))
    s += code_block(
        "getHashPath(index):\n"
        "  pairs ← []\n\n"
        "  for level = 0 to depth-1:\n"
        "    pos   ← index >> level\n"
        "    left  ← getNode(level, pos & ~1)   // even sibling\n"
        "    right ← getNode(level, pos |  1)   // odd  sibling\n"
        "    pairs.append( (left, right) )\n\n"
        "  return HashPath(pairs)\n\n"
        "Complexity: O(d) DB reads"
    )

    s.append(Paragraph("3.3  Database Key Schema", H2))
    s.append(Paragraph(
        "All nodes are stored as 32-byte SHA-256 hashes under string keys:", BODY))
    db_tbl = section_table(
        [Paragraph(b("Key"), BODY), Paragraph(b("Value"), BODY), Paragraph(b("Purpose"), BODY)],
        [
            [tt('"name"'),           "40 bytes: root (32) + depth (4 LE)",  "Tree metadata"],
            [tt('"name:level:pos"'), "32 bytes: SHA-256 hash",               "Node at (level, pos)"],
        ],
        col_widths=[4.5*cm, 7*cm, 6*cm],
    )
    s.append(db_tbl)
    s.append(Spacer(1, 0.3*cm))
    s.append(Paragraph(
        "The metadata key is written atomically together with all path nodes "
        "using a single database batch — important for crash-consistency.", BODY))

    # ── 4. TypeScript Implementation ──────────────────────────────────────────
    s.append(Paragraph("4. TypeScript Implementation", H1))
    s.append(Paragraph(
        "File: " + tt("eng-sessions/merkle-tree/src/merkle_tree.ts"), BODY))

    s.append(Paragraph("4.1  Constructor and Zero-Hash Pre-computation", H2))
    s += code_block(
        "constructor(private db: LevelUp, private name: string,\n"
        "            private depth: number, root?: Buffer) {\n"
        "  if (!(depth >= 1 && depth <= MAX_DEPTH)) throw Error('Bad depth');\n\n"
        "  this.zeroHashes = this.computeZeroHashes(depth);\n\n"
        "  if (root) {\n"
        "    this.root = root;                  // restoring from DB\n"
        "  } else {\n"
        "    this.root = this.zeroHashes[depth]; // fresh empty tree\n"
        "  }\n"
        "}\n\n"
        "private computeZeroHashes(depth: number): Buffer[] {\n"
        "  const zeros: Buffer[] = new Array(depth + 1);\n"
        "  zeros[0] = this.hasher.hash(Buffer.alloc(LEAF_BYTES));\n"
        "  for (let i = 1; i <= depth; i++)\n"
        "    zeros[i] = this.hasher.compress(zeros[i-1], zeros[i-1]);\n"
        "  return zeros;\n"
        "}",
        "TypeScript: constructor initialises zero hashes and sets root"
    )

    s.append(Paragraph("4.2  updateElement", H2))
    s += code_block(
        "async updateElement(index: number, value: Buffer) {\n"
        "  const batch = this.db.batch();\n"
        "  let currentHash = this.hasher.hash(value);\n"
        "  let pos = index;\n\n"
        "  for (let level = 0; level < this.depth; level++) {\n"
        "    batch.put(this.nodeKey(level, pos), currentHash);\n\n"
        "    const siblingPos = pos ^ 1;\n"
        "    const sibling = await this.getNode(level, siblingPos);\n\n"
        "    currentHash = (pos % 2 === 0)\n"
        "      ? this.hasher.compress(currentHash, sibling)\n"
        "      : this.hasher.compress(sibling, currentHash);\n\n"
        "    pos = pos >> 1;\n"
        "  }\n\n"
        "  this.root = currentHash;\n"
        "  this.writeMetaData(batch);\n"
        "  await batch.write();\n"
        "  return this.root;\n"
        "}",
        "TypeScript: updateElement — path traversal with batched writes"
    )

    s.append(Paragraph("4.3  getHashPath", H2))
    s += code_block(
        "async getHashPath(index: number) {\n"
        "  const pairs: Buffer[][] = [];\n\n"
        "  for (let level = 0; level < this.depth; level++) {\n"
        "    const pos      = index >> level;\n"
        "    const leftPos  = pos & ~1;\n"
        "    const rightPos = pos | 1;\n\n"
        "    const left  = await this.getNode(level, leftPos);\n"
        "    const right = await this.getNode(level, rightPos);\n\n"
        "    pairs.push([left, right]);\n"
        "  }\n\n"
        "  return new HashPath(pairs);\n"
        "}",
        "TypeScript: getHashPath — returns sibling pairs from leaf to root"
    )

    s.append(Paragraph("4.4  Test Results", H2))
    ts_tbl = section_table(
        [Paragraph(b("#"), BODY), Paragraph(b("Description"), BODY),
         Paragraph(b("Expected Root"), BODY), Paragraph(b("Pass"), BODY)],
        [
            ["1", "Empty depth-32 tree root",            tt("1c9a7e5f…"), "✓"],
            ["2", "Depth-2, 4 leaves, root + hash paths",tt("e645e6b5…"), "✓"],
            ["3", "Depth-10, 128 inserts, restore DB",   tt("4b8404d0…"), "✓"],
            ["4", "Depth-32, 1024 inserts, path[100]",   tt("26996bfc…"), "✓"],
        ],
        col_widths=[1.2*cm, 7.5*cm, 5.5*cm, 2.3*cm],
    )
    s.append(ts_tbl)

    # ── 5. C++ Implementation ─────────────────────────────────────────────────
    s.append(Paragraph("5. C++20 Implementation", H1))
    s.append(Paragraph(
        "File: " + tt("eng-sessions/merkle-tree-cpp/src/merkle_tree.hpp"), BODY))

    s.append(Paragraph("5.1  Constructor", H2))
    s += code_block(
        "MerkleTree(MockDB& db, const std::string& name,\n"
        "           uint32_t depth, const sha256_hash_t& root = {})\n"
        "    : db(db), name(name), depth(depth), root(root), hasher()\n"
        "{\n"
        "    if (!(depth >= 1 && depth <= MAX_DEPTH))\n"
        "        throw std::runtime_error(\"Bad depth\");\n\n"
        "    // Pre-compute z_0 ... z_depth\n"
        "    zero_hashes.resize(depth + 1);\n"
        "    zero_hashes[0] = hasher.hash(std::vector<uint8_t>(LEAF_BYTES, 0));\n"
        "    for (uint32_t i = 1; i <= depth; ++i)\n"
        "        zero_hashes[i] = hasher.compress(zero_hashes[i-1], zero_hashes[i-1]);\n\n"
        "    // Restore root from DB if present\n"
        "    auto stored = db.get(name);\n"
        "    if (stored.has_value()) {\n"
        "        this->root = stored.value();\n"
        "    } else {\n"
        "        this->root = zero_hashes[depth];\n"
        "        db.put(name, this->root);\n"
        "    }\n"
        "}",
        "C++: constructor with DB restoration"
    )

    s.append(Paragraph("5.2  update_element", H2))
    s += code_block(
        "sha256_hash_t update_element(uint64_t index,\n"
        "                              const std::vector<uint8_t>& value)\n"
        "{\n"
        "    if (value.size() != LEAF_BYTES)\n"
        "        throw std::runtime_error(\"Value must be exactly 64 bytes.\");\n\n"
        "    std::vector<MockDBBatchItem> batch;\n"
        "    sha256_hash_t current_hash = hasher.hash(value);\n"
        "    uint64_t pos = index;\n\n"
        "    for (uint32_t level = 0; level < depth; ++level) {\n"
        "        batch.push_back({ node_key(level, pos), current_hash });\n\n"
        "        uint64_t sibling_pos = pos ^ uint64_t(1);\n"
        "        sha256_hash_t sibling = get_node(level, sibling_pos);\n\n"
        "        if (pos % 2 == 0)\n"
        "            current_hash = hasher.compress(current_hash, sibling);\n"
        "        else\n"
        "            current_hash = hasher.compress(sibling, current_hash);\n\n"
        "        pos >>= 1;\n"
        "    }\n\n"
        "    root = current_hash;\n"
        "    batch.push_back({ name, root });\n"
        "    db.batch_write(batch);\n"
        "    return root;\n"
        "}",
        "C++: update_element — leaf update with batch write"
    )

    s.append(Paragraph("5.3  get_hash_path", H2))
    s += code_block(
        "HashPath get_hash_path(uint64_t index) const\n"
        "{\n"
        "    std::vector<std::pair<sha256_hash_t, sha256_hash_t>> pairs;\n"
        "    pairs.reserve(depth);\n\n"
        "    for (uint32_t level = 0; level < depth; ++level) {\n"
        "        uint64_t pos       = index >> level;\n"
        "        uint64_t left_pos  = pos & ~uint64_t(1);\n"
        "        uint64_t right_pos = pos | uint64_t(1);\n\n"
        "        sha256_hash_t left  = get_node(level, left_pos);\n"
        "        sha256_hash_t right = get_node(level, right_pos);\n\n"
        "        pairs.push_back({ left, right });\n"
        "    }\n\n"
        "    return HashPath(pairs);\n"
        "}",
        "C++: get_hash_path — returns sibling pairs from leaf to root"
    )

    s.append(Paragraph("5.4  Private Helper Methods", H2))
    s += code_block(
        "// Build the database key for node at (level, position)\n"
        "std::string node_key(uint32_t level, uint64_t pos) const\n"
        "{\n"
        "    return name + \":\" + std::to_string(level)\n"
        "                + \":\" + std::to_string(pos);\n"
        "}\n\n"
        "// Get node from DB, falling back to zero_hashes[level] if absent\n"
        "sha256_hash_t get_node(uint32_t level, uint64_t pos) const\n"
        "{\n"
        "    auto stored = db.get(node_key(level, pos));\n"
        "    if (stored.has_value()) return stored.value();\n"
        "    return zero_hashes[level];\n"
        "}"
    )

    s.append(Paragraph("5.5  Test Results", H2))
    cpp_tbl = section_table(
        [Paragraph(b("#"), BODY), Paragraph(b("Description"), BODY),
         Paragraph(b("Expected Root"), BODY), Paragraph(b("Pass"), BODY)],
        [
            ["1", "Empty depth-32 tree root",            tt("1c9a7e5f…"), "✓"],
            ["2", "Depth-2, 4 leaves, root + hash paths",tt("e645e6b5…"), "✓"],
            ["3", "Depth-10, 128 inserts, restore DB",   tt("4b8404d0…"), "✓"],
            ["4", "Depth-32, 1024 inserts, path[100]",   tt("26996bfc…"), "✓"],
        ],
        col_widths=[1.2*cm, 7.5*cm, 5.5*cm, 2.3*cm],
    )
    s.append(cpp_tbl)

    # ── 6. Topics Covered ──────────────────────────────────────────────────────
    s.append(Paragraph("6. Topics Covered — What This Problem Tests", H1))

    s.append(Paragraph("6.1  Core Data Structures & Algorithms", H2))
    s += [
        bullet(b("Binary trees and tree traversal") +
               ": leaf-to-root path traversal — identical pattern to B-tree node-splitting "
               "and red-black tree rotations."),
        bullet(b("Sparse data structures") +
               ": zero-hash placeholders avoid materialising 2³² nodes. "
               "Used in Ethereum's Patricia Merkle Trie, Solana's account tree, and Aztec's world state."),
        bullet(b("Hash functions as commitments") +
               ": SHA-256 is collision-resistant so modifying any leaf changes the root detectably."),
        bullet(b("Bit manipulation") +
               ": XOR for sibling (p ^ 1), AND-NOT for left child (p & ~1), "
               "OR for right child (p | 1), right-shift for level ascent (p >> k)."),
        bullet(b("Amortised complexity") +
               ": O(d) operations per update, O(N·d) total for N insertions."),
    ]

    s.append(Paragraph("6.2  Cryptography Topics", H2))
    s += [
        bullet(b("SHA-256") + ": Merkle–Damgård construction, 64 rounds, 256-bit output. "
               "Collision resistance ensures distinct trees produce distinct roots."),
        bullet(b("Merkle trees in practice") + ": Bitcoin transaction Merkle roots, "
               "Ethereum state roots, certificate transparency (RFC 6962), IPFS CIDs, Git tree objects."),
        bullet(b("Merkle proofs") + ": O(log N) membership proof. "
               "A proof for a depth-32 tree is exactly 32 × 64 = 2,048 bytes."),
        bullet(b("Commitment schemes") + ": updating one leaf re-commits all ancestors "
               "in O(d) time — critical for rollup state transitions."),
        bullet(b("zkSNARK context") + ": the hash path is passed as a private witness "
               "into PLONK/Honk circuits. The circuit re-hashes it in-circuit to verify "
               "membership without revealing the leaf value."),
    ]

    s.append(Paragraph("6.3  Systems and Engineering Topics", H2))
    s += [
        bullet(b("Key–value persistence") + ": designing a key schema ("
               + tt("name:level:pos") + ") for O(1) lookup of any tree node."),
        bullet(b("Batched atomic writes") + ": grouping all path updates and metadata "
               "into one batch prevents partial writes on crash."),
        bullet(b("DB restoration") + ": serialising tree state (root + depth) so a "
               "new object can resume exactly where the previous one left off."),
        bullet(b("Async/await patterns") + " (TypeScript): LevelUp is Promise-based; "
               "all reads are awaited while writes are buffered in a batch."),
        bullet(b("C++20 features") + ": " + tt("std::optional") + " for nullable DB results, "
               + tt("std::array<uint8_t,32>") + " for fixed-size hashes, "
               + tt("std::vector<MockDBBatchItem>") + " for atomic writes."),
    ]

    s.append(Paragraph("6.4  Aztec-Specific Context", H2))
    s += [
        bullet(b("Note commitment tree") + ": sparse Merkle tree storing UTXO commitments; "
               "root is included in every Aztec block header."),
        bullet(b("Nullifier tree") + ": indexed Merkle tree preventing double-spend "
               "without revealing which note was spent (privacy-preserving)."),
        bullet(b("Archive tree") + ": stores historical block headers, enabling proofs "
               "about past state."),
        bullet(b("Barretenberg / Noir circuits") + ": the getHashPath result feeds directly "
               "into zero-knowledge membership proofs compiled with Noir."),
    ]

    # ── 7. Complexity Summary ─────────────────────────────────────────────────
    s.append(Paragraph("7. Complexity Summary", H1))
    cplx_tbl = section_table(
        [Paragraph(b("Operation"), BODY), Paragraph(b("Time"), BODY), Paragraph(b("Space"), BODY)],
        [
            ["Constructor (zero hashes)", "O(d) hash ops",                  "O(d)"],
            ["updateElement",             "O(d) hash ops + O(d) DB I/O",    "O(d)"],
            ["getHashPath",               "O(d) DB reads",                   "O(d)"],
            ["getRoot",                   "O(1)",                            "O(1)"],
            ["Total storage (N inserts)", "O(N·d) writes",                  "O(N·d) nodes"],
        ],
        col_widths=[5.5*cm, 6*cm, 5*cm],
    )
    s.append(cplx_tbl)
    s.append(Spacer(1, 0.3*cm))
    s.append(Paragraph(
        "With d = 32: each updateElement call touches exactly 32 nodes on the path "
        "from leaf to root. Inserting 1,024 leaves (as in Test 4) performs "
        "1,024 × 32 = 32,768 hash compressions and the same number of DB writes.",
        BODY))

    # ── 8. Conclusion ─────────────────────────────────────────────────────────
    s.append(Paragraph("8. Conclusion", H1))
    s.append(Paragraph(
        "Both the TypeScript and C++ Merkle tree implementations pass all eight "
        "test cases.  The four key design choices are:", BODY))
    s += [
        bullet(b("Pre-computed zero hashes") + " in the constructor handle sparse nodes "
               "without any storage overhead."),
        bullet(b("String key schema") + " (" + tt("name:level:pos") + ") provides O(1) "
               "DB lookup for any node."),
        bullet(b("Single-loop traversal") + " from leaf to root for both writes "
               "(updateElement) and reads (getHashPath)."),
        bullet(b("Atomic batch writes") + " ensure the tree state is always consistent, "
               "including the metadata root update."),
    ]
    s.append(Spacer(1, 0.5*cm))
    s.append(hr(thickness=2))
    s.append(Paragraph(
        "✓  4 TypeScript tests passing  |  ✓  4 C++ tests passing  |  "
        "All expected hashes verified",
        ParagraphStyle("Final", parent=BODY, alignment=TA_CENTER,
                       textColor=AZTEC_PURPLE, fontName="Helvetica-Bold", fontSize=11)))
    s.append(hr(thickness=2))

    return s


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    doc = BaseDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        rightMargin=2.5*cm, leftMargin=2.5*cm,
        topMargin=2.8*cm,   bottomMargin=2.5*cm,
    )
    doc.addPageTemplates([make_page_template(doc)])
    story = build_story()
    doc.build(story)
    print(f"PDF written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
