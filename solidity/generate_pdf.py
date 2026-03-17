"""
Generate a comprehensive PDF covering all three Aztec DeFi Bridge challenge options.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Preformatted, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors

OUTPUT = '/home/user/aztec-interview-tests/solidity/solution.pdf'

AZTEC  = HexColor('#6414C8')
PURPLE = HexColor('#4a148c')
GREEN  = HexColor('#1b5e20')
BLUE   = HexColor('#0d47a1')
CODE_BG = HexColor('#f5f5f5')
HDR_BG  = HexColor('#7c3aed')
ROW_ALT = HexColor('#f0eafb')

# ── Page template ─────────────────────────────────────────────────────────────
def make_template(doc):
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(AZTEC)
        canvas.rect(doc.leftMargin - 0.5*cm, A4[1] - 2.0*cm,
                    doc.width + 1*cm, 0.55*cm, fill=1, stroke=0)
        canvas.setFillColor(white)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(doc.leftMargin, A4[1] - 1.72*cm,
                          'Aztec Technical Challenge — DeFi Bridge Solutions')
        canvas.drawRightString(A4[0] - doc.rightMargin, A4[1] - 1.72*cm,
                               'solidity/')
        canvas.setFillColor(colors.grey)
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(A4[0]/2, 1.2*cm, f'Page {doc.page}')
        canvas.restoreState()
    return PageTemplate(id='main', frames=[frame], onPage=on_page)

# ── Styles ─────────────────────────────────────────────────────────────────────
S = getSampleStyleSheet()
H1   = ParagraphStyle('H1',  parent=S['Heading1'], textColor=AZTEC, fontSize=18,
                      fontName='Helvetica-Bold', spaceAfter=8, spaceBefore=20)
H2   = ParagraphStyle('H2',  parent=S['Heading2'], textColor=AZTEC, fontSize=14,
                      fontName='Helvetica-Bold', spaceAfter=6, spaceBefore=14)
H3   = ParagraphStyle('H3',  parent=S['Heading3'], textColor=PURPLE, fontSize=12,
                      fontName='Helvetica-Bold', spaceAfter=4, spaceBefore=10)
BODY = ParagraphStyle('Body', parent=S['Normal'], fontSize=10.5, leading=15,
                      spaceAfter=6, alignment=TA_JUSTIFY)
BULL = ParagraphStyle('Bull', parent=BODY, leftIndent=18, firstLineIndent=-10,
                      spaceAfter=4)
CODE = ParagraphStyle('Code', parent=S['Code'], fontName='Courier', fontSize=8.2,
                      leading=11.5, leftIndent=10, rightIndent=10,
                      backColor=CODE_BG, spaceAfter=8, spaceBefore=4,
                      borderColor=HexColor('#cccccc'), borderWidth=0.5,
                      borderPadding=6)
TITLE_S  = ParagraphStyle('Title', parent=S['Title'], textColor=AZTEC, fontSize=24,
                           fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)
SUB_S    = ParagraphStyle('Sub', parent=S['Normal'], fontSize=12, alignment=TA_CENTER,
                           textColor=HexColor('#555555'), spaceAfter=16)
CAPTION  = ParagraphStyle('Cap', parent=S['Normal'], fontSize=9,
                           textColor=colors.grey, alignment=TA_CENTER, spaceAfter=6)
FINAL_S  = ParagraphStyle('Final', parent=BODY, alignment=TA_CENTER,
                           textColor=AZTEC, fontName='Helvetica-Bold', fontSize=11)

def hr(thick=1.5): return HRFlowable(width='100%', thickness=thick, color=AZTEC,
                                     spaceAfter=6, spaceBefore=6)
def b(t): return f'<b>{t}</b>'
def tt(t): return f"<font name='Courier'>{t}</font>"
def ul(t): return Paragraph(f'\u2022\u2002{t}', BULL)
def code(src, cap=''):
    r = [Preformatted(src.strip(), CODE)]
    if cap: r.append(Paragraph(cap, CAPTION))
    return r

def tbl(headers, rows, widths=None):
    data = [headers] + rows
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,0), HDR_BG),
        ('TEXTCOLOR',     (0,0),(-1,0), white),
        ('FONTNAME',      (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,0), 10),
        ('TOPPADDING',    (0,0),(-1,0), 7),
        ('BOTTOMPADDING', (0,0),(-1,0), 7),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [white, ROW_ALT]),
        ('FONTNAME',      (0,1),(-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1),(-1,-1), 9.5),
        ('GRID',          (0,0),(-1,-1), 0.3, HexColor('#cccccc')),
        ('TOPPADDING',    (0,1),(-1,-1), 6),
        ('BOTTOMPADDING', (0,1),(-1,-1), 6),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('RIGHTPADDING',  (0,0),(-1,-1), 8),
    ]))
    return t

# =============================================================================
def story():
    s = []

    # ── Title page ────────────────────────────────────────────────────────────
    s += [Spacer(1, 1.5*cm), hr(3),
          Paragraph('Aztec DeFi Bridge — All Options', TITLE_S),
          Paragraph('Aztec Technical Challenge · Full Solution Document', SUB_S),
          hr(3), Spacer(1, 0.4*cm)]

    info = [
        ['Project',  'solidity/ — Aztec Connect DeFi Bridge'],
        ['Option 1', 'Enhanced UniswapBridge  (token↔token, slippage, pair-exists check)'],
        ['Option 2', 'AaveLendingBridge  (virtual-asset positions, async withdrawal)'],
        ['Option 3', 'NettingBridge  (ETH/TOKEN netting, async finalise)'],
        ['Tests',    '✓  7 / 7 passing  (Option 1 fully tested on in-process Hardhat chain)'],
    ]
    t = Table(info, colWidths=[3.5*cm, 13*cm])
    t.setStyle(TableStyle([
        ('FONTNAME',  (0,0),(0,-1), 'Helvetica-Bold'),
        ('FONTNAME',  (1,0),(1,-1), 'Helvetica'),
        ('FONTSIZE',  (0,0),(-1,-1), 10),
        ('TOPPADDING',(0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING',(0,0),(-1,-1), 8),
        ('GRID',      (0,0),(-1,-1), 0.3, HexColor('#cccccc')),
        ('ROWBACKGROUNDS',(0,0),(-1,-1), [white, ROW_ALT]),
    ]))
    s += [t, PageBreak()]

    # =========================================================================
    # 1. AZTEC BRIDGE MODEL
    # =========================================================================
    s.append(Paragraph('1. The Aztec Bridge Model', H1))
    s.append(Paragraph(
        'A DeFi bridge is a Layer-1 Solidity contract that exposes a DeFi protocol '
        'through a standard interface the Aztec rollup understands.  Aztec batches '
        'many users\' private transactions by bridge ID, then makes a single on-chain '
        'call that amortises gas over all participants.', BODY))

    s.append(Paragraph('1.1  Interface', H2))
    s += code(
        'interface IDefiBridge {\n'
        '    // Synchronous or async DeFi interaction.\n'
        '    function convert(\n'
        '        Types.AztecAsset[4] calldata assets,\n'
        '        uint64  auxData,        // 64-bit bridge-specific config\n'
        '        uint256 interactionNonce,\n'
        '        uint256 inputValue\n'
        '    ) external payable\n'
        '      returns (uint256 outputValueA, uint256 outputValueB, bool isAsync);\n\n'
        '    // Returns true when async interaction is ready to finalise.\n'
        '    function canFinalise(...) external view returns (bool);\n\n'
        '    // Completes async interaction; transfers output assets to proxy.\n'
        '    function finalise(...) external payable\n'
        '      returns (uint256 outputValueA, uint256 outputValueB);\n'
        '}',
        'IDefiBridge.sol — every bridge must implement this interface'
    )

    s.append(Paragraph('1.2  Asset Types', H2))
    s.append(tbl(
        [Paragraph(b('Type'), BODY), Paragraph(b('Value'), BODY), Paragraph(b('Meaning'), BODY)],
        [['ETH',     '1', 'Native Ether'],
         ['ERC20',   '2', 'Any ERC-20 token; address in erc20Address field'],
         ['VIRTUAL', '3', 'Aztec position token; id = interactionNonce of the open call'],
         ['NOT_USED','0', 'Slot unused for this interaction']],
        widths=[3.5*cm, 2*cm, 11*cm],
    ))

    s.append(Paragraph('1.3  Synchronous vs Asynchronous', H2))
    s += [
        ul(b('Synchronous') + ': ' + tt('convert()') + ' returns output assets immediately '
           '(' + tt('isAsync = false') + ').  The proxy verifies balances changed by '
           'exactly outputValueA / outputValueB.'),
        ul(b('Asynchronous') + ': ' + tt('convert()') + ' returns ' + tt('isAsync = true') +
           ' with both output values = 0.  The rollup later polls ' + tt('canFinalise()') +
           ' and calls ' + tt('finalise()') + ' when ready.'),
    ]

    s.append(Paragraph('1.4  Bridge ID Encoding', H2))
    s += code(
        'BridgeId (248 bits)\n'
        '( auxData || bitConfig || outputAssetB || outputAssetA || inputAssetB || inputAssetA || bridgeAddressId )\n'
        '    64           32            30             30              30             30               32\n\n'
        'BitConfig (32 bits)\n'
        '( unused || firstAssetVirtual || secondAssetValid || secondAssetVirtual )\n'
        '    29              1                   1                    1'
    )
    s.append(Paragraph(
        'The bridge ID encodes everything Aztec needs to route a transaction.  '
        'All users with the same bridge ID are batched together into one L1 call, '
        'sharing gas costs proportionally.', BODY))

    s += [PageBreak()]

    # =========================================================================
    # 2. OPTION 1 — ENHANCED UNISWAP BRIDGE
    # =========================================================================
    s.append(Paragraph('2. Option 1 — Enhanced UniswapBridge', H1))
    s.append(Paragraph(
        'The original bridge only handled ETH↔ERC20 swaps with no slippage control '
        'and no pair-existence check.  Three improvements were implemented.', BODY))

    s.append(Paragraph('2.1  Token-to-Token Swaps (ERC20 → ERC20)', H2))
    s.append(Paragraph(
        'Uniswap V2 has no direct ERC20↔ERC20 pairs for arbitrary tokens.  '
        'The standard pattern routes through WETH as an intermediary:'
        ' Token A → WETH → Token B.', BODY))
    s += code(
        '} else if (\n'
        '    assets[0].assetType == Types.AztecAssetType.ERC20 &&\n'
        '    assets[2].assetType == Types.AztecAssetType.ERC20\n'
        ') {\n'
        '    address[] memory path = new address[](3);\n'
        '    path[0] = assets[0].erc20Address;   // Token A\n'
        '    path[1] = weth;                      // intermediate WETH\n'
        '    path[2] = assets[2].erc20Address;   // Token B\n\n'
        '    _requirePairExists(path[0], path[1]);\n'
        '    _requirePairExists(path[1], path[2]);\n\n'
        '    IERC20(tokenIn).approve(address(router), inputValue);\n'
        '    amounts = router.swapExactTokensForTokens(\n'
        '        inputValue, amountOutMin, path, defiBridgeProxy, deadline\n'
        '    );\n'
        '    outputValueA = amounts[amounts.length - 1];\n'
        '}',
        'UniswapBridge.sol — ERC20→ERC20 branch in convert()'
    )

    s.append(Paragraph('2.2  Slippage Control via auxData', H2))
    s.append(Paragraph(
        'The unused ' + tt('auxData') + ' parameter now carries the maximum acceptable '
        'slippage in <b>basis points</b> (1 BPS = 0.01%).  '
        'Setting ' + tt('auxData = 0') + ' disables the check (amountOutMin = 0).  '
        'Setting ' + tt('auxData = 500') + ' means "reject if output < 95 % of expected".', BODY))
    s += code(
        'function _calcAmountOutMin(\n'
        '    uint256 inputValue,\n'
        '    address[] memory path,\n'
        '    uint64 auxData\n'
        ') internal view returns (uint256) {\n'
        '    if (auxData == 0) return 0;       // no protection\n\n'
        '    uint256[] memory expected = router.getAmountsOut(inputValue, path);\n'
        '    uint256 expectedOut = expected[expected.length - 1];\n\n'
        '    // Require at least (1 - auxData/10000) of expected output.\n'
        '    return expectedOut.mul(uint256(10000).sub(auxData)).div(10000);\n'
        '}',
        'UniswapBridge.sol — _calcAmountOutMin helper'
    )

    s.append(Paragraph('2.3  Pair Existence Check', H2))
    s.append(Paragraph(
        'Rather than letting Uniswap silently fail or behave unexpectedly with '
        'zero-liquidity pairs, the bridge queries the factory directly:', BODY))
    s += code(
        'function _requirePairExists(address tokenA, address tokenB) internal view {\n'
        '    address pair = IUniswapV2Factory(factory).getPair(tokenA, tokenB);\n'
        '    require(pair != address(0), \'UniswapBridge: PAIR_DOES_NOT_EXIST\');\n'
        '}',
        'Reverts immediately if no liquidity pool exists for the given pair'
    )

    s.append(Paragraph('2.4  Test Results (7 / 7 passing)', H2))
    s.append(tbl(
        [Paragraph(b('#'), BODY), Paragraph(b('Test'), BODY),
         Paragraph(b('auxData'), BODY), Paragraph(b('Pass'), BODY)],
        [['1', 'ETH → ERC20 (original)',                 '0',   '✓'],
         ['2', 'ERC20 → ETH',                            '0',   '✓'],
         ['3', 'ERC20 → ERC20 (via WETH)',               '0',   '✓'],
         ['4', 'ETH → ERC20 with 5 % slippage guard',    '500', '✓'],
         ['5', 'ERC20→ERC20 with 1 % slippage guard',    '100', '✓'],
         ['6', 'Revert — no Uniswap pair exists',        '0',   '✓'],
         ['7', 'Revert — incompatible asset types',      '0',   '✓']],
        widths=[1.2*cm, 8.5*cm, 3*cm, 2*cm],
    ))

    s.append(Paragraph('2.5  Complete convert() Logic', H2))
    s += code(
        'function convert(assets, auxData, , inputValue) {\n'
        '    require(msg.sender == defiBridgeProxy);\n'
        '    isAsync = false;\n\n'
        '    if (ETH → ERC20) {\n'
        '        path = [weth, tokenOut]\n'
        '        _requirePairExists(weth, tokenOut)\n'
        '        amountOutMin = _calcAmountOutMin(inputValue, path, auxData)\n'
        '        outputValueA = router.swapExactETHForTokens{value}(amountOutMin, ...)[last]\n\n'
        '    } else if (ERC20 → ETH) {\n'
        '        path = [tokenIn, weth]\n'
        '        _requirePairExists(tokenIn, weth)\n'
        '        approve(router, inputValue)\n'
        '        amountOutMin = _calcAmountOutMin(inputValue, path, auxData)\n'
        '        outputValueA = router.swapExactTokensForETH(inputValue, amountOutMin, ...)[last]\n\n'
        '    } else if (ERC20 → ERC20) {\n'
        '        path = [tokenIn, weth, tokenOut]\n'
        '        _requirePairExists(tokenIn, weth)\n'
        '        _requirePairExists(weth, tokenOut)\n'
        '        approve(router, inputValue)\n'
        '        amountOutMin = _calcAmountOutMin(inputValue, path, auxData)\n'
        '        outputValueA = router.swapExactTokensForTokens(inputValue, amountOutMin, ...)[last]\n\n'
        '    } else { revert(INCOMPATIBLE_ASSET_PAIR) }\n'
        '}'
    )

    s += [PageBreak()]

    # =========================================================================
    # 3. OPTION 2 — AAVE LENDING BRIDGE
    # =========================================================================
    s.append(Paragraph('3. Option 2 — AaveLendingBridge', H1))
    s.append(Paragraph(
        'A new bridge that deposits assets into <b>Aave V2</b> to earn yield, '
        'using Aztec\'s virtual asset mechanism to represent the position and '
        'async completion to allow interest to accrue before withdrawal.', BODY))

    s.append(Paragraph('3.1  Design Rationale', H2))
    s += [
        ul(b('Virtual assets') + ' eliminate the need to mint ERC-20 receipt tokens, '
           'saving gas and keeping position data private inside Aztec.'),
        ul(b('Async flow') + ' allows users to lock funds for an arbitrary period.  '
           'Withdrawals via ' + tt('finalise()') + ' automatically collect principal '
           '+ all accrued interest in one step.'),
        ul(b('aToken accounting') + ': Aave aTokens rebase continuously.  Holding '
           'them in the bridge contract means the user automatically earns interest '
           'with no additional calls.'),
    ]

    s.append(Paragraph('3.2  Asset Flow Diagram', H2))
    s += code(
        '┌─────────────────────────────── OPEN POSITION ─────────────────────────────┐\n'
        '│  inputAssetA = ERC20 / ETH         outputAssetA = VIRTUAL (id = nonce)    │\n'
        '│                                                                            │\n'
        '│  convert():                                                                │\n'
        '│    approve lendingPool for ERC20 (or use WETHGateway for ETH)             │\n'
        '│    lendingPool.deposit(asset, amount, bridge, 0)                          │\n'
        '│    bridge now holds aTokens                                               │\n'
        '│    outputValueA = inputValue  (1:1 virtual accounting)                    │\n'
        '│    isAsync = false  ← synchronous deposit                                 │\n'
        '└────────────────────────────────────────────────────────────────────────────┘\n\n'
        '┌─────────────────────────────── CLOSE POSITION ────────────────────────────┐\n'
        '│  inputAssetA = VIRTUAL (id = open nonce)   outputAssetA = ERC20 / ETH     │\n'
        '│                                                                            │\n'
        '│  convert():                                                                │\n'
        '│    positions[openNonce].readyToFinalise = true                             │\n'
        '│    isAsync = true  ← deferred withdrawal                                  │\n'
        '│                                                                            │\n'
        '│  canFinalise(): always true (Aave V2 has no withdrawal lock)               │\n'
        '│                                                                            │\n'
        '│  finalise():                                                               │\n'
        '│    lendingPool.withdraw(asset, type(uint256).max, bridge)                  │\n'
        '│    transfers principal + interest to DefiBridgeProxy                      │\n'
        '│    outputValueA = actual amount withdrawn (> deposit if interest accrued)  │\n'
        '└────────────────────────────────────────────────────────────────────────────┘'
    )

    s.append(Paragraph('3.3  Key Contract Structures', H2))
    s += code(
        'struct Position {\n'
        '    address underlying;        // deposited token (address(0) = ETH)\n'
        '    address aToken;            // Aave aToken received on deposit\n'
        '    uint256 depositedAmount;   // principal\n'
        '    bool    readyToFinalise;   // set true by close convert()\n'
        '}\n\n'
        'mapping(uint256 => Position) public positions;          // openNonce → Position\n'
        'mapping(uint256 => uint256)  public closeToOpenNonce;   // closeNonce → openNonce'
    )

    s.append(Paragraph('3.4  Interest Accrual', H2))
    s.append(Paragraph(
        'Aave aTokens are rebasing tokens: their balance increases continuously '
        'as interest accrues.  Since the bridge holds aTokens between open and close, '
        'calling ' + tt('lendingPool.withdraw(asset, type(uint256).max, ...)') +
        ' withdraws the entire aToken balance, which automatically includes all '
        'accrued interest.  The user receives ' + b('more') + ' than they deposited '
        'without any extra steps.', BODY))

    s.append(Paragraph('3.5  Supported Interaction Patterns', H2))
    s.append(tbl(
        [Paragraph(b('Pattern'), BODY), Paragraph(b('Input A'), BODY),
         Paragraph(b('Output A'), BODY), Paragraph(b('Async?'), BODY),
         Paragraph(b('Use case'), BODY)],
        [['1→4 (open)', 'ERC20 / ETH', 'VIRTUAL', 'No',  'Deposit to Aave'],
         ['2→1 (close)', 'VIRTUAL',    'ERC20 / ETH', 'Yes', 'Withdraw + interest']],
        widths=[2.5*cm, 3*cm, 3*cm, 2*cm, 6*cm],
    ))

    s += [PageBreak()]

    # =========================================================================
    # 4. OPTION 3 — NETTING BRIDGE
    # =========================================================================
    s.append(Paragraph('4. Option 3 — NettingBridge', H1))
    s.append(Paragraph(
        'An advanced bridge that <b>nets opposing trades</b> within the same rollup '
        'batch before touching Uniswap, dramatically reducing fees and price impact '
        'for users.', BODY))

    s.append(Paragraph('4.1  Why Netting Matters', H2))
    s.append(Paragraph(
        'Without netting, if 1 000 users buy TOKEN with ETH and 900 users sell '
        'TOKEN for ETH in the same batch, the rollup would execute two full swaps '
        'on Uniswap — paying fees and slippage on the entire notional of both legs.  '
        'With netting, only the 100-unit imbalance is traded on-chain, reducing '
        'Uniswap fees by ~90 %.', BODY))

    s.append(Paragraph('4.2  Netting Algorithm', H2))
    s += code(
        '// Inputs held by the bridge after both convert() calls:\n'
        '//   ethAmount   = ETH from leg A (ETH→TOKEN)\n'
        '//   tokenAmount = TOKEN from leg B (TOKEN→ETH)\n\n'
        'ethLegValueToken = getAmountsOut(ethAmount, [WETH, TOKEN])[1]\n\n'
        'if ethLegValueToken >= tokenAmount:\n'
        '    ┌── Case A: ETH leg is worth more ──────────────────────────────────┐\n'
        '    │  ethEquivOfToken = getAmountsIn(tokenAmount, [WETH, TOKEN])[0]    │\n'
        '    │  residualEth = ethAmount - ethEquivOfToken                         │\n'
        '    │  tokenFromSwap = swapExactETHForTokens(residualEth)               │\n'
        '    │                                                                    │\n'
        '    │  Leg A output (TOKEN): tokenAmount + tokenFromSwap                │\n'
        '    │  Leg B output (ETH):   ethEquivOfToken                            │\n'
        '    └────────────────────────────────────────────────────────────────────┘\n'
        'else:\n'
        '    ┌── Case B: TOKEN leg is worth more ────────────────────────────────┐\n'
        '    │  residualToken = tokenAmount - ethLegValueToken                   │\n'
        '    │  ethFromSwap = swapExactTokensForETH(residualToken)               │\n'
        '    │                                                                    │\n'
        '    │  Leg A output (TOKEN): ethLegValueToken  (direct net)             │\n'
        '    │  Leg B output (ETH):   ethAmount + ethFromSwap                    │\n'
        '    └────────────────────────────────────────────────────────────────────┘'
    )

    s.append(Paragraph('4.3  Worked Example', H2))
    s += code(
        'Liquidity: 1 000 ETH and 2 000 000 TOKEN in the Uniswap pool\n'
        'Price:     ~2 000 TOKEN / ETH\n\n'
        'Leg A (ETH→TOKEN):  1 ETH   in → ? TOKEN out\n'
        'Leg B (TOKEN→ETH):  1 800 TOKEN in → ? ETH out\n\n'
        'ethLegValueToken = getAmountsOut(1 ETH) ≈ 1 996 TOKEN\n'
        '→ Case A applies (1 996 TOKEN ≥ 1 800 TOKEN)\n\n'
        'ethEquivOfToken = getAmountsIn(1 800 TOKEN) ≈ 0.902 ETH\n'
        'residualEth     = 1 - 0.902 = 0.098 ETH\n'
        'tokenFromSwap   = swapExactETHForTokens(0.098 ETH) ≈ 195 TOKEN\n\n'
        '→ Leg A (ETH→TOKEN) user receives:  1 800 + 195 = 1 995 TOKEN\n'
        '→ Leg B (TOKEN→ETH) user receives:  0.902 ETH\n\n'
        'Without netting:\n'
        '  Leg A: swap 1 ETH   → 1 992 TOKEN  (full Uniswap trade)\n'
        '  Leg B: swap 1 800 TOKEN → 0.897 ETH  (full Uniswap trade)\n\n'
        'Savings: ~5 TOKEN for leg-A user, ~0.005 ETH for leg-B user\n'
        '         (fee saved = 0.3 % × 1 800 TOKEN worth of netting ≈ 5.4 TOKEN)'
    )

    s.append(Paragraph('4.4  Async Flow', H2))
    s += [
        ul(tt('convert(ETH→TOKEN, nonce1)') +
           ': stores ETH amount, sets ' + tt('hasPendingEthToToken = true') +
           ', returns ' + tt('isAsync = true') + '.'),
        ul(tt('convert(TOKEN→ETH, nonce2)') +
           ': triggers netting via ' + tt('_netCaseA / _netCaseB') +
           ', marks both positions ready, returns ' + tt('isAsync = true') + '.'),
        ul(tt('canFinalise(nonce1)') + ' and ' + tt('canFinalise(nonce2)') +
           ': return ' + tt('true') + ' once both are ready.'),
        ul(tt('finalise(nonce1)') +
           ': transfers TOKEN to DefiBridgeProxy.'),
        ul(tt('finalise(nonce2)') +
           ': transfers ETH to DefiBridgeProxy.'),
    ]

    s.append(Paragraph('4.5  Storage Layout', H2))
    s += code(
        'struct PendingInteraction {\n'
        '    Direction direction;    // ETH_TO_TOKEN or TOKEN_TO_ETH\n'
        '    uint256   inputValue;   // original input amount\n'
        '    uint256   outputValue;  // computed by _net(), transferred in finalise()\n'
        '    bool      ready;        // true once _net() completes\n'
        '}\n\n'
        'mapping(uint256 => PendingInteraction) public pendingInteractions;\n\n'
        'uint256 public pendingEthToTokenNonce;  // nonce of the open ETH leg\n'
        'bool    public hasPendingEthToToken;    // guard: prevents two ETH legs at once'
    )

    s += [PageBreak()]

    # =========================================================================
    # 5. TOPICS COVERED
    # =========================================================================
    s.append(Paragraph('5. Topics Covered', H1))

    s.append(Paragraph('5.1  Solidity Patterns', H2))
    s += [
        ul(b('Interface conformance') + ': all bridges implement ' +
           tt('IDefiBridge') + ', enabling the proxy to call them generically.'),
        ul(b('Immutable state variables') + ': ' + tt('defiBridgeProxy') + ', ' +
           tt('weth') + ', ' + tt('factory') + ' are set once in the constructor and '
           'marked ' + tt('immutable') + ' for gas efficiency (~100 gas saved per read '
           'vs. storage slot).'),
        ul(b('SafeMath') + ': all arithmetic uses ' + tt('SafeMath') +
           ' to prevent overflow/underflow (required for Solidity < 0.8.0 which lacks '
           'built-in checks).'),
        ul(b('Storage cleanup') + ': ' + tt('AaveLendingBridge') + ' uses ' +
           tt('delete') + ' to zero out Position structs after finalisation, '
           'earning a gas refund and preventing stale-state bugs.'),
        ul(b('Stack-too-deep avoidance') + ': ' + tt('NettingBridge._net') +
           ' splits the netting into two internal functions (' + tt('_netCaseA') +
           ', ' + tt('_netCaseB') + ') to stay within the EVM\'s 16-variable local '
           'stack limit.'),
    ]

    s.append(Paragraph('5.2  DeFi Protocol Knowledge', H2))
    s += [
        ul(b('Uniswap V2 AMM') + ': constant-product formula x·y = k; '
           'all swaps touch WETH as the routing hub; ' +
           tt('getAmountsOut') + '/' + tt('getAmountsIn') + ' for price discovery.'),
        ul(b('Aave V2 lending') + ': rebasing aTokens; ' +
           tt('deposit()') + '/' + tt('withdraw()') + ' interface; WETHGateway '
           'for ETH positions; referral codes.'),
        ul(b('Slippage') + ': basis-point encoding, ' + tt('amountOutMin') +
           ' guard, price impact vs. fee cost trade-off.'),
        ul(b('Liquidity bootstrapping') + ': creating Uniswap pairs with ' +
           tt('factory.createPair()') + ' and low-level ' + tt('pair.mint()') +
           ' without the router (test setup).'),
    ]

    s.append(Paragraph('5.3  Aztec Connect Concepts', H2))
    s += [
        ul(b('Bridge IDs and batching') + ': same bridge ID → same rollup batch → '
           'amortised L1 gas across all participating users.'),
        ul(b('Virtual assets') + ': gas-efficient position tokens that live inside '
           'Aztec without an on-chain ERC-20 deployment; id = interactionNonce.'),
        ul(b('Asynchronous flow') + ': deferred settlement pattern for positions that '
           'need time to accrue (lending interest, option expiry, bridged L2 state).'),
        ul(b('Netting') + ': the optimal batching strategy for bilateral markets; '
           'reduces both Uniswap fees (0.3 % per swap) and price impact (especially '
           'relevant for large notionals).'),
        ul(b('auxData') + ': 64-bit opaque field allowing each bridge to encode its '
           'own configuration (slippage tolerance, token IDs, unlock timestamps, etc.).'),
    ]

    s.append(Paragraph('5.4  Security Considerations', H2))
    s += [
        ul(b('Caller validation') + ': every entry point checks '
           + tt('msg.sender == defiBridgeProxy') + ' to prevent unauthorised calls '
           'that could drain the bridge.'),
        ul(b('Pair-existence guard') + ': '
           + tt('_requirePairExists') + ' prevents sending ETH or tokens to '
           'zero-liquidity pools where recovery is uncertain.'),
        ul(b('Reentrancy') + ': the bridge sends ETH to the proxy via '
           + tt('.transfer()') + ' (2 300 gas stipend) which prevents reentrancy into '
           'complex logic.  Full reentrancy guards would be added in production.'),
        ul(b('Approval hygiene') + ': ' + tt('approve(router, inputValue)') +
           ' grants exactly the needed amount, never an unlimited allowance.'),
    ]

    s += [PageBreak()]

    # =========================================================================
    # 6. SUMMARY
    # =========================================================================
    s.append(Paragraph('6. Summary', H1))
    s.append(tbl(
        [Paragraph(b('Option'), BODY), Paragraph(b('Contract'), BODY),
         Paragraph(b('Key features'), BODY), Paragraph(b('Status'), BODY)],
        [
            ['1', tt('UniswapBridge.sol'),
             'ETH↔ERC20, ERC20↔ERC20 (via WETH), slippage guard (BPS), pair-exists check',
             '✓ Impl + 7 tests'],
            ['2', tt('AaveLendingBridge.sol'),
             'Aave V2 deposit/withdraw, virtual asset position tokens, async interest accrual',
             '✓ Impl'],
            ['3', tt('NettingBridge.sol'),
             'ETH/TOKEN netting, Case A/B algorithm, async finalise, gas savings',
             '✓ Impl'],
        ],
        widths=[1.8*cm, 5.5*cm, 8.2*cm, 3*cm],
    ))
    s.append(Spacer(1, 0.5*cm))
    s.append(hr(2))
    s.append(Paragraph(
        '✓  All three options implemented  |  ✓  7 / 7 Option-1 tests passing  |  '
        '✓  All 14 contracts compile cleanly with Solidity 0.7.3',
        FINAL_S))
    s.append(hr(2))
    return s


def main():
    doc = BaseDocTemplate(
        OUTPUT, pagesize=A4,
        rightMargin=2.5*cm, leftMargin=2.5*cm,
        topMargin=2.8*cm,   bottomMargin=2.5*cm,
    )
    doc.addPageTemplates([make_template(doc)])
    doc.build(story())
    print(f'PDF written to: {OUTPUT}')


if __name__ == '__main__':
    main()
