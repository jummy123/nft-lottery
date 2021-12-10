pragma solidity ^0.8.0;

import "OpenZeppelin/openzeppelin-contracts@4.3.3/contracts/access/Ownable.sol";
import "OpenZeppelin/openzeppelin-contracts@4.3.3/contracts/interfaces/IERC721.sol";

import "./IStrategy.sol";


contract Treasury is Ownable {

    // The balance of the refundable deposits.
    uint public refundableBalance = 0;

    // A mapping storing allowances winners can withdraw.
    mapping(uint => uint) public winAllowances;

    IStrategy public strategy;

    function withdraw(address account, uint amount) external onlyOwner {
        refundableBalance = refundableBalance - amount;
        // If we have an active strategy we need to withdraw our funds form there.
        if (address(strategy) != address(0)) {
            strategy.withdraw(amount);
        }
        payable(account).transfer(amount);
    }

    function deposit() external payable onlyOwner {
        refundableBalance = refundableBalance + msg.value;
        if (address(strategy) != address(0)) {
            strategy.invest{value: msg.value}();
        }
    }

    /// @notice Withdraw any winnings owed to a ticket.
    function withdrawWinnings(uint ticketId) public {
        IERC721 lottery = IERC721(owner());
        require(lottery.ownerOf(ticketId) == msg.sender, 'Cannot claim winnings if not ticket owner');
        require(winAllowances[ticketId] > 0, 'No winnings to collect');

        payable(msg.sender).transfer(winAllowances[ticketId]);
        winAllowances[ticketId] = 0;
    }

    /// @notice The current prize pool for upcoming draw.
    /// @dev This is the yield we have currently generated from the lending protocol.
    function currentPrize() public view returns (uint) {
        return strategy.balanceOfUnderlying() - refundableBalance;
    }

    // XXX: We need governance for this, only the lottery should be able to set
    // the strategy. Removed now for testing.
    function setStrategy(address strategyAddress) external {
        strategy = IStrategy(strategyAddress);
    }

    receive() external payable {}
}
