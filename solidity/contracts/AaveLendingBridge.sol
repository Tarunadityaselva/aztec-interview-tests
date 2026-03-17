// SPDX-License-Identifier: GPL-2.0-only
pragma solidity >=0.6.6 <0.8.0;
pragma experimental ABIEncoderV2;

import {SafeMath} from '@openzeppelin/contracts/math/SafeMath.sol';
import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';
import {IDefiBridge} from './interfaces/IDefiBridge.sol';
import {Types} from './Types.sol';

/**
 * @title AaveLendingBridge
 * @notice Option 2 — A DeFi bridge that deposits assets into Aave V2 lending pools,
 *         using Aztec virtual assets to represent the position and async finalisation
 *         to allow interest to accrue before withdrawal.
 *
 * ## Asset flow
 *
 *   Open position (synchronous deposit):
 *     inputAssetA  = ERC20 token (e.g. DAI, USDC)  OR  ETH
 *     outputAssetA = VIRTUAL (the position token, id = interactionNonce)
 *     → Bridge wraps ETH to WETH if needed, calls IAaveLendingPool.deposit(),
 *       receives aTokens, and holds them.
 *     → isAsync = false; outputValueA = inputValue (tracks the deposit amount).
 *
 *   Close position (asynchronous withdrawal):
 *     inputAssetA  = VIRTUAL (the position token returned when opening)
 *     outputAssetA = ERC20 token or ETH (same underlying as the open)
 *     → convert() marks the interaction as "pending withdrawal"; isAsync = true.
 *     → canFinalise() always returns true (Aave V2 is liquid; no lock-up).
 *     → finalise() calls IAaveLendingPool.withdraw(), receives underlying +
 *       accrued interest, and transfers it to the DefiBridgeProxy.
 *
 * ## Notes
 *   • aTokens are held by this bridge contract between open and close.
 *   • Any interest earned between deposit and withdrawal is automatically
 *     reflected in the aToken balance at withdrawal time.
 *   • The `auxData` field can encode a future unlock timestamp for
 *     time-locked strategies; not used in this baseline implementation.
 */

// ── Minimal Aave V2 interfaces ────────────────────────────────────────────────

interface IAaveLendingPool {
    /**
     * @dev Deposits `amount` of `asset` into the Aave lending pool,
     *      minting a corresponding amount of aTokens to `onBehalfOf`.
     */
    function deposit(
        address asset,
        uint256 amount,
        address onBehalfOf,
        uint16 referralCode
    ) external;

    /**
     * @dev Withdraws `amount` of `asset` from the Aave lending pool.
     *      Burns the corresponding aTokens held by `msg.sender`.
     * @return The actual amount withdrawn (may be > amount if all is specified).
     */
    function withdraw(
        address asset,
        uint256 amount,
        address to
    ) external returns (uint256);
}

interface IAaveWETHGateway {
    /**
     * @dev Deposits ETH into Aave (wraps to WETH internally).
     */
    function depositETH(
        address lendingPool,
        address onBehalfOf,
        uint16 referralCode
    ) external payable;

    /**
     * @dev Withdraws ETH from Aave (unwraps from WETH internally).
     */
    function withdrawETH(
        address lendingPool,
        uint256 amount,
        address to
    ) external;
}

// ─────────────────────────────────────────────────────────────────────────────

contract AaveLendingBridge is IDefiBridge {
    using SafeMath for uint256;

    // ── Storage ───────────────────────────────────────────────────────────────

    address public immutable defiBridgeProxy;
    IAaveLendingPool public immutable lendingPool;
    IAaveWETHGateway public immutable wethGateway;

    /**
     * @dev Tracks each open lending position.
     *
     * @param underlying   Address of the deposited token (address(0) = ETH).
     * @param aToken       Address of the Aave aToken received on deposit.
     * @param depositedAmount  Principal deposited (used for accounting).
     * @param readyToFinalise  True once the user has requested withdrawal via convert().
     */
    struct Position {
        address underlying;
        address aToken;
        uint256 depositedAmount;
        bool    readyToFinalise;
    }

    /// @dev interactionNonce of the OPEN call → position data
    mapping(uint256 => Position) public positions;

    /// @dev interactionNonce of the CLOSE call → open nonce it references
    mapping(uint256 => uint256) public closeToOpenNonce;

    // ── Constructor ───────────────────────────────────────────────────────────

    /**
     * @param _defiBridgeProxy  Address of the Aztec rollup's DefiBridgeProxy.
     * @param _lendingPool      Address of the Aave V2 LendingPool contract.
     * @param _wethGateway      Address of the Aave WETHGateway for ETH deposits.
     */
    constructor(
        address _defiBridgeProxy,
        address _lendingPool,
        address _wethGateway
    ) public {
        defiBridgeProxy = _defiBridgeProxy;
        lendingPool     = IAaveLendingPool(_lendingPool);
        wethGateway     = IAaveWETHGateway(_wethGateway);
    }

    receive() external payable {}

    // ── IDefiBridge ───────────────────────────────────────────────────────────

    /**
     * @notice Handles both opening (ERC20/ETH → VIRTUAL) and closing
     *         (VIRTUAL → ERC20/ETH) of lending positions.
     *
     *  Open:   inputAssetA is ERC20 or ETH, outputAssetA is VIRTUAL → synchronous.
     *  Close:  inputAssetA is VIRTUAL, outputAssetA is ERC20 or ETH  → async.
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
            bool    isAsync
        )
    {
        require(msg.sender == defiBridgeProxy, 'AaveLendingBridge: INVALID_CALLER');

        bool inputIsReal  = assets[0].assetType == Types.AztecAssetType.ETH ||
                            assets[0].assetType == Types.AztecAssetType.ERC20;
        bool outputIsVirt = assets[2].assetType == Types.AztecAssetType.VIRTUAL;
        bool inputIsVirt  = assets[0].assetType == Types.AztecAssetType.VIRTUAL;
        bool outputIsReal = assets[2].assetType == Types.AztecAssetType.ETH ||
                            assets[2].assetType == Types.AztecAssetType.ERC20;

        if (inputIsReal && outputIsVirt) {
            // ── OPEN: deposit underlying → hold aTokens, return virtual position ──
            address underlying;
            address aToken;

            if (assets[0].assetType == Types.AztecAssetType.ETH) {
                // Deposit ETH via the WETHGateway.
                underlying = address(0);
                // aWETH address must be looked up from lendingPool; simplified here.
                aToken = address(0); // caller must supply correct aToken via auxData in prod
                wethGateway.depositETH{value: inputValue}(
                    address(lendingPool), address(this), 0
                );
            } else {
                // Deposit ERC20.
                underlying = assets[0].erc20Address;
                aToken     = address(0); // derive from Aave's getReserveData() in production
                IERC20(underlying).approve(address(lendingPool), inputValue);
                lendingPool.deposit(underlying, inputValue, address(this), 0);
            }

            positions[interactionNonce] = Position({
                underlying:      underlying,
                aToken:          aToken,
                depositedAmount: inputValue,
                readyToFinalise: false
            });

            // The virtual asset's id = interactionNonce, owned by the Aztec user.
            outputValueA = inputValue; // 1:1 accounting; actual value tracked via aToken
            isAsync      = false;

        } else if (inputIsVirt && outputIsReal) {
            // ── CLOSE: mark position for withdrawal ──────────────────────────
            // The virtual asset id passed in assets[0].id equals the open nonce.
            uint256 openNonce = assets[0].id;
            require(positions[openNonce].depositedAmount > 0, 'AaveLendingBridge: UNKNOWN_POSITION');

            positions[openNonce].readyToFinalise = true;
            closeToOpenNonce[interactionNonce]   = openNonce;

            // Async: actual withdrawal happens in finalise().
            outputValueA = 0;
            isAsync      = true;

        } else {
            revert('AaveLendingBridge: INVALID_ASSET_PAIR');
        }
    }

    /**
     * @notice Returns true once the close interaction is ready to finalise.
     *         For Aave V2 (no lock-up), this is always true once convert() marks
     *         the position as readyToFinalise.
     */
    function canFinalise(
        Types.AztecAsset[4] calldata /*assets*/,
        uint64  /*auxData*/,
        uint256 interactionNonce
    ) external view override returns (bool) {
        uint256 openNonce = closeToOpenNonce[interactionNonce];
        return positions[openNonce].readyToFinalise;
    }

    /**
     * @notice Executes the Aave withdrawal and transfers underlying + interest
     *         back to the DefiBridgeProxy.
     */
    function finalise(
        Types.AztecAsset[4] calldata assets,
        uint64  /*auxData*/,
        uint256 interactionNonce
    )
        external
        payable
        override
        returns (uint256 outputValueA, uint256 /*outputValueB*/)
    {
        require(msg.sender == defiBridgeProxy, 'AaveLendingBridge: INVALID_CALLER');

        uint256 openNonce = closeToOpenNonce[interactionNonce];
        Position storage pos = positions[openNonce];
        require(pos.readyToFinalise, 'AaveLendingBridge: NOT_READY');

        // Withdraw all accrued aTokens (principal + interest) from Aave.
        uint256 withdrawn;
        if (pos.underlying == address(0)) {
            // ETH position: withdraw via WETHGateway.
            uint256 ethBefore = address(this).balance;
            wethGateway.withdrawETH(address(lendingPool), type(uint256).max, address(this));
            withdrawn = address(this).balance.sub(ethBefore);
            payable(defiBridgeProxy).transfer(withdrawn);
        } else {
            // ERC20 position: withdraw directly.
            uint256 balBefore = IERC20(pos.underlying).balanceOf(address(this));
            lendingPool.withdraw(pos.underlying, type(uint256).max, address(this));
            withdrawn = IERC20(pos.underlying).balanceOf(address(this)).sub(balBefore);
            IERC20(pos.underlying).transfer(defiBridgeProxy, withdrawn);
        }

        outputValueA = withdrawn;

        // Clean up storage.
        delete positions[openNonce];
        delete closeToOpenNonce[interactionNonce];
    }
}
