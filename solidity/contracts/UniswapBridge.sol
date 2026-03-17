// SPDX-License-Identifier: GPL-2.0-only
// Copyright 2020 Spilsbury Holdings Ltd
pragma solidity >=0.6.6 <0.8.0;
pragma experimental ABIEncoderV2;

import {SafeMath} from '@openzeppelin/contracts/math/SafeMath.sol';
import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';

import {IUniswapV2Factory} from '@uniswap/v2-core/contracts/interfaces/IUniswapV2Factory.sol';
import {IUniswapV2Router02} from '@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol';

import {IDefiBridge} from './interfaces/IDefiBridge.sol';
import {Types} from './Types.sol';

// import 'hardhat/console.sol';

contract UniswapBridge is IDefiBridge {
    using SafeMath for uint256;

    address public immutable defiBridgeProxy;
    address public immutable weth;
    address public immutable factory;

    IUniswapV2Router02 router;

    constructor(address _defiBridgeProxy, address _router) public {
        defiBridgeProxy = _defiBridgeProxy;
        router = IUniswapV2Router02(_router);
        weth = router.WETH();
        factory = router.factory();
    }

    receive() external payable {}

    /**
     * @notice Executes a swap via Uniswap V2.
     *
     * @param assets  [inputAssetA, inputAssetB (unused), outputAssetA, outputAssetB (unused)]
     *                Supported combinations:
     *                  ETH  → ERC20  : direct pair via WETH
     *                  ERC20 → ETH   : direct pair via WETH
     *                  ERC20 → ERC20 : two-hop route through WETH
     *
     * @param auxData Max slippage tolerance in basis points (BPS).
     *                0     = no protection (amountOutMin = 0).
     *                100   = 1 % max slippage  (accept ≥ 99 % of expected output).
     *                500   = 5 % max slippage  (accept ≥ 95 % of expected output).
     *                10000 = 100% slippage (effectively no minimum – same as 0).
     *
     * @param inputValue Amount of input asset to swap (wei for ETH, token units for ERC20).
     */
    function convert(
        Types.AztecAsset[4] calldata assets,
        uint64 auxData,
        uint256 /*interactionNonce*/,
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
        require(msg.sender == defiBridgeProxy, 'UniswapBridge: INVALID_CALLER');
        isAsync = false;

        uint256 deadline = block.timestamp;

        if (
            assets[0].assetType == Types.AztecAssetType.ETH &&
            assets[2].assetType == Types.AztecAssetType.ERC20
        ) {
            // ── ETH → ERC20 ────────────────────────────────────────────────
            address[] memory path = new address[](2);
            path[0] = weth;
            path[1] = assets[2].erc20Address;

            _requirePairExists(path[0], path[1]);

            uint256 amountOutMin = _calcAmountOutMin(inputValue, path, auxData);
            uint256[] memory amounts = router.swapExactETHForTokens{value: inputValue}(
                amountOutMin, path, defiBridgeProxy, deadline
            );
            outputValueA = amounts[amounts.length - 1];

        } else if (
            assets[0].assetType == Types.AztecAssetType.ERC20 &&
            assets[2].assetType == Types.AztecAssetType.ETH
        ) {
            // ── ERC20 → ETH ────────────────────────────────────────────────
            address[] memory path = new address[](2);
            path[0] = assets[0].erc20Address;
            path[1] = weth;

            _requirePairExists(path[0], path[1]);

            require(
                IERC20(assets[0].erc20Address).approve(address(router), inputValue),
                'UniswapBridge: APPROVE_FAILED'
            );
            uint256 amountOutMin = _calcAmountOutMin(inputValue, path, auxData);
            uint256[] memory amounts = router.swapExactTokensForETH(
                inputValue, amountOutMin, path, defiBridgeProxy, deadline
            );
            outputValueA = amounts[amounts.length - 1];

        } else if (
            assets[0].assetType == Types.AztecAssetType.ERC20 &&
            assets[2].assetType == Types.AztecAssetType.ERC20
        ) {
            // ── ERC20 → ERC20 (routed through WETH) ───────────────────────
            address tokenIn  = assets[0].erc20Address;
            address tokenOut = assets[2].erc20Address;

            // Build a 3-hop path: tokenIn → WETH → tokenOut.
            address[] memory path = new address[](3);
            path[0] = tokenIn;
            path[1] = weth;
            path[2] = tokenOut;

            _requirePairExists(path[0], path[1]);
            _requirePairExists(path[1], path[2]);

            require(
                IERC20(tokenIn).approve(address(router), inputValue),
                'UniswapBridge: APPROVE_FAILED'
            );
            uint256 amountOutMin = _calcAmountOutMin(inputValue, path, auxData);
            uint256[] memory amounts = router.swapExactTokensForTokens(
                inputValue, amountOutMin, path, defiBridgeProxy, deadline
            );
            outputValueA = amounts[amounts.length - 1];

        } else {
            revert('UniswapBridge: INCOMPATIBLE_ASSET_PAIR');
        }
    }

    // ── View functions ────────────────────────────────────────────────────────

    function canFinalise(
        Types.AztecAsset[4] calldata,
        uint64,
        uint256
    ) external view override returns (bool) {
        return false;
    }

    function finalise(
        Types.AztecAsset[4] calldata,
        uint64,
        uint256
    ) external payable override returns (uint256, uint256) {
        require(false);
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    /**
     * @dev Reverts if the Uniswap V2 pair for (tokenA, tokenB) does not exist.
     *      Uses the factory's getPair which returns address(0) for non-existent pairs.
     */
    function _requirePairExists(address tokenA, address tokenB) internal view {
        address pair = IUniswapV2Factory(factory).getPair(tokenA, tokenB);
        require(pair != address(0), 'UniswapBridge: PAIR_DOES_NOT_EXIST');
    }

    /**
     * @dev Calculates the minimum acceptable output amount based on slippage tolerance.
     *
     * @param inputValue  The amount being swapped.
     * @param path        The swap path.
     * @param auxData     Max slippage in basis points (0 = no minimum, 100 = 1%, 500 = 5%).
     * @return amountOutMin  0 when auxData is 0, otherwise
     *                       floor( expectedOut * (10000 - auxData) / 10000 ).
     */
    function _calcAmountOutMin(
        uint256 inputValue,
        address[] memory path,
        uint64 auxData
    ) internal view returns (uint256 amountOutMin) {
        if (auxData == 0) {
            return 0;
        }
        uint256[] memory expectedAmounts = router.getAmountsOut(inputValue, path);
        uint256 expectedOut = expectedAmounts[expectedAmounts.length - 1];
        // Require at least (1 - auxData/10000) of the expected output.
        amountOutMin = expectedOut.mul(uint256(10000).sub(uint256(auxData))).div(10000);
    }
}
