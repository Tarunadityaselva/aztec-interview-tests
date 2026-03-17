// SPDX-License-Identifier: GPL-2.0-only
pragma solidity >=0.6.6 <0.8.0;
pragma experimental ABIEncoderV2;

import {SafeMath} from '@openzeppelin/contracts/math/SafeMath.sol';
import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';
import {IUniswapV2Factory} from '@uniswap/v2-core/contracts/interfaces/IUniswapV2Factory.sol';
import {IUniswapV2Router02} from '@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol';
import {IDefiBridge} from './interfaces/IDefiBridge.sol';
import {Types} from './Types.sol';

/**
 * @title NettingBridge
 * @notice Option 3 — An Aztec DeFi bridge that nets opposite-direction trades
 *         on an ETH/TOKEN pair before routing only the imbalance through Uniswap.
 *
 * ## Why netting?
 *   When Aztec batches many user transactions together it frequently sees both
 *   sides of a market (e.g. some users buy TOKEN with ETH while others sell
 *   TOKEN for ETH).  Without netting, every unit of TOKEN is sold twice — once
 *   in each direction — paying Uniswap fees and suffering price impact on the
 *   full notional.  By netting the two legs first, only the *residual* imbalance
 *   touches Uniswap, dramatically reducing fees and slippage.
 *
 * ## Protocol assumptions (per the spec)
 *   • Two different bridge IDs both point to this contract.
 *   • Bridge ID A: input ETH,   output TOKEN  (call-1)
 *   • Bridge ID B: input TOKEN, output ETH    (call-2)
 *   • The rollup always calls convert(A) before convert(B) within a batch.
 *   • Both calls return isAsync = true; the rollup later calls canFinalise /
 *     finalise for each.
 *
 * ## Flow
 *   1. convert(ETH→TOKEN) is called.
 *      - ETH is transferred to this contract by DefiBridgeProxy beforehand.
 *      - Stored as a pending position; returns isAsync = true.
 *
 *   2. convert(TOKEN→ETH) is called (same batch).
 *      - TOKEN is transferred to this contract by DefiBridgeProxy beforehand.
 *      - Net calculation:
 *          ethValue  = getAmountsOut(ethAmount, [WETH, TOKEN])[1]
 *          (i.e. how many TOKENs the ETH leg is worth at current price)
 *
 *          Case A — ETH leg > TOKEN leg (more ETH value than TOKEN value):
 *            • deltaToken = ethValue - tokenAmount
 *            • Swap only deltaEthEquiv of ETH for deltaToken on Uniswap.
 *            • ETH→TOKEN side receives: tokenAmount + deltaToken = ethValue (approx)
 *            • TOKEN→ETH side receives: ethAmount - deltaEthEquiv
 *
 *          Case B — TOKEN leg ≥ ETH leg:
 *            • deltaToken = tokenAmount - ethValue
 *            • Swap only deltaToken for ETH on Uniswap.
 *            • ETH→TOKEN side receives: ethValue (from the TOKEN input)
 *            • TOKEN→ETH side receives: ethAmount + ethFromSwap
 *
 *      - Both pending positions are marked ready.
 *      - Returns isAsync = true.
 *
 *   3. canFinalise returns true for both nonces once step 2 is done.
 *
 *   4. finalise(nonce_A) sends TOKEN to DefiBridgeProxy.
 *      finalise(nonce_B) sends ETH  to DefiBridgeProxy.
 */
contract NettingBridge is IDefiBridge {
    using SafeMath for uint256;

    // ── Types ─────────────────────────────────────────────────────────────────

    enum Direction { ETH_TO_TOKEN, TOKEN_TO_ETH }

    struct PendingInteraction {
        Direction direction;
        uint256   inputValue;
        uint256   outputValue;
        bool      ready;
    }

    // ── State ─────────────────────────────────────────────────────────────────

    address public immutable defiBridgeProxy;
    address public immutable weth;
    address public immutable token;    // the TOKEN in ETH/TOKEN pair
    IUniswapV2Router02 public immutable router;

    /// @dev nonce → pending interaction
    mapping(uint256 => PendingInteraction) public pendingInteractions;

    /// @dev Nonce of the pending ETH→TOKEN call (set by convert A, cleared by convert B).
    uint256 public pendingEthToTokenNonce;
    bool    public hasPendingEthToToken;

    // ── Constructor ───────────────────────────────────────────────────────────

    /**
     * @param _defiBridgeProxy  Address of the Aztec rollup's DefiBridgeProxy.
     * @param _router           Address of the Uniswap V2 Router.
     * @param _token            Address of the TOKEN asset in the ETH/TOKEN pair.
     */
    constructor(
        address _defiBridgeProxy,
        address _router,
        address _token
    ) public {
        defiBridgeProxy = _defiBridgeProxy;
        router          = IUniswapV2Router02(_router);
        weth            = IUniswapV2Router02(_router).WETH();
        token           = _token;

        // Verify the pair exists.
        address factory = IUniswapV2Router02(_router).factory();
        require(
            IUniswapV2Factory(factory).getPair(IUniswapV2Router02(_router).WETH(), _token) != address(0),
            'NettingBridge: PAIR_DOES_NOT_EXIST'
        );
    }

    receive() external payable {}

    // ── IDefiBridge ───────────────────────────────────────────────────────────

    /**
     * @notice Handles ETH→TOKEN (call-1) and TOKEN→ETH (call-2) legs.
     *         Both always return isAsync = true.
     */
    function convert(
        Types.AztecAsset[4] calldata assets,
        uint64 /*auxData*/,
        uint256 interactionNonce,
        uint256 inputValue
    )
        external
        payable
        override
        returns (
            uint256 outputValueA,
            uint256 /*outputValueB*/,
            bool isAsync
        )
    {
        require(msg.sender == defiBridgeProxy, 'NettingBridge: INVALID_CALLER');
        isAsync      = true;
        outputValueA = 0;

        bool isEthToToken = assets[0].assetType == Types.AztecAssetType.ETH &&
                            assets[2].assetType == Types.AztecAssetType.ERC20;
        bool isTokenToEth = assets[0].assetType == Types.AztecAssetType.ERC20 &&
                            assets[2].assetType == Types.AztecAssetType.ETH;

        if (isEthToToken) {
            // ── Leg A: ETH → TOKEN ───────────────────────────────────────────
            require(!hasPendingEthToToken, 'NettingBridge: ETH_LEG_ALREADY_PENDING');

            pendingInteractions[interactionNonce] = PendingInteraction({
                direction:   Direction.ETH_TO_TOKEN,
                inputValue:  inputValue,
                outputValue: 0,
                ready:       false
            });
            pendingEthToTokenNonce = interactionNonce;
            hasPendingEthToToken   = true;

        } else if (isTokenToEth) {
            // ── Leg B: TOKEN → ETH (triggers netting) ────────────────────────
            require(hasPendingEthToToken, 'NettingBridge: NO_ETH_LEG_PENDING');

            uint256 ethAmount   = pendingInteractions[pendingEthToTokenNonce].inputValue;
            uint256 tokenAmount = inputValue;

            _net(pendingEthToTokenNonce, interactionNonce, ethAmount, tokenAmount);

            // Store leg B.
            pendingInteractions[interactionNonce] = PendingInteraction({
                direction:   Direction.TOKEN_TO_ETH,
                inputValue:  tokenAmount,
                outputValue: pendingInteractions[interactionNonce].outputValue,  // set by _net
                ready:       true
            });

            hasPendingEthToToken = false;

        } else {
            revert('NettingBridge: INCOMPATIBLE_ASSET_PAIR');
        }
    }

    function canFinalise(
        Types.AztecAsset[4] calldata /*assets*/,
        uint64  /*auxData*/,
        uint256 interactionNonce
    ) external view override returns (bool) {
        return pendingInteractions[interactionNonce].ready;
    }

    /**
     * @notice Transfers the netted output asset to DefiBridgeProxy.
     */
    function finalise(
        Types.AztecAsset[4] calldata /*assets*/,
        uint64  /*auxData*/,
        uint256 interactionNonce
    )
        external
        payable
        override
        returns (uint256 outputValueA, uint256 /*outputValueB*/)
    {
        require(msg.sender == defiBridgeProxy, 'NettingBridge: INVALID_CALLER');

        PendingInteraction storage p = pendingInteractions[interactionNonce];
        require(p.ready, 'NettingBridge: NOT_READY');

        outputValueA = p.outputValue;

        if (p.direction == Direction.ETH_TO_TOKEN) {
            // Transfer TOKEN to the proxy.
            require(
                IERC20(token).transfer(defiBridgeProxy, outputValueA),
                'NettingBridge: TOKEN_TRANSFER_FAILED'
            );
        } else {
            // Transfer ETH to the proxy.
            payable(defiBridgeProxy).transfer(outputValueA);
        }

        delete pendingInteractions[interactionNonce];
    }

    // ── Internal netting logic ────────────────────────────────────────────────

    /**
     * @dev Nets the two legs and executes only the residual swap on Uniswap.
     *
     * @param ethToTokenNonce  Nonce of the pending ETH→TOKEN leg.
     * @param tokenToEthNonce  Nonce of the current TOKEN→ETH leg.
     * @param ethAmount        ETH from the first leg.
     * @param tokenAmount      TOKEN from the second leg.
     *
     * After this call:
     *   pendingInteractions[ethToTokenNonce].outputValue = TOKEN to send to leg-A user
     *   pendingInteractions[ethToTokenNonce].ready       = true
     *   pendingInteractions[tokenToEthNonce].outputValue = ETH  to send to leg-B user
     */
    function _net(
        uint256 ethToTokenNonce,
        uint256 tokenToEthNonce,
        uint256 ethAmount,
        uint256 tokenAmount
    ) internal {
        address[] memory ethToTokenPath = new address[](2);
        ethToTokenPath[0] = weth;
        ethToTokenPath[1] = token;

        uint256 ethLegValueToken = router.getAmountsOut(ethAmount, ethToTokenPath)[1];

        if (ethLegValueToken >= tokenAmount) {
            _netCaseA(ethToTokenNonce, tokenToEthNonce, ethAmount, tokenAmount, ethToTokenPath);
        } else {
            _netCaseB(ethToTokenNonce, tokenToEthNonce, ethAmount, tokenAmount, ethLegValueToken);
        }
    }

    /// @dev Case A: ETH leg value >= TOKEN leg. Swap residual ETH for TOKEN.
    function _netCaseA(
        uint256 ethToTokenNonce,
        uint256 tokenToEthNonce,
        uint256 ethAmount,
        uint256 tokenAmount,
        address[] memory ethToTokenPath
    ) internal {
        uint256 ethEquivOfToken = router.getAmountsIn(tokenAmount, ethToTokenPath)[0];
        uint256 residualEth     = ethAmount.sub(ethEquivOfToken);

        uint256 tokenFromSwap = router.swapExactETHForTokens{value: residualEth}(
            0, ethToTokenPath, address(this), block.timestamp
        )[1];

        // Leg A (ETH→TOKEN): receives tokenAmount netted + tokenFromSwap from swap.
        pendingInteractions[ethToTokenNonce].outputValue = tokenAmount.add(tokenFromSwap);
        pendingInteractions[ethToTokenNonce].ready       = true;

        // Leg B (TOKEN→ETH): receives the ETH equivalent that was netted.
        pendingInteractions[tokenToEthNonce].outputValue = ethEquivOfToken;
    }

    /// @dev Case B: TOKEN leg value > ETH leg. Swap residual TOKEN for ETH.
    function _netCaseB(
        uint256 ethToTokenNonce,
        uint256 tokenToEthNonce,
        uint256 ethAmount,
        uint256 tokenAmount,
        uint256 ethLegValueToken
    ) internal {
        uint256 residualToken = tokenAmount.sub(ethLegValueToken);

        address[] memory tokenToEthPath = new address[](2);
        tokenToEthPath[0] = token;
        tokenToEthPath[1] = weth;

        IERC20(token).approve(address(router), residualToken);
        uint256 ethFromSwap = router.swapExactTokensForETH(
            residualToken, 0, tokenToEthPath, address(this), block.timestamp
        )[1];

        // Leg A (ETH→TOKEN): receives the TOKEN-equivalent that was netted.
        pendingInteractions[ethToTokenNonce].outputValue = ethLegValueToken;
        pendingInteractions[ethToTokenNonce].ready       = true;

        // Leg B (TOKEN→ETH): receives ethAmount netted + ethFromSwap from swap.
        pendingInteractions[tokenToEthNonce].outputValue = ethAmount.add(ethFromSwap);
    }
}
