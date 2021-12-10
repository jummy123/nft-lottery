pragma solidity ^0.8.0;

import "OpenZeppelin/openzeppelin-contracts@4.3.3/contracts/access/Ownable.sol";
import './IStrategy.sol';


contract DummyStrategy is Ownable, IStrategy {

    function invest() external payable onlyOwner {}

    function withdraw(uint amount) external onlyOwner {
        payable(msg.sender).transfer(amount);
    }

    function balanceOfUnderlying() public view returns (uint) {
        return address(this).balance;
    }

    /// @dev This function is here so we can simulate a yield by
    ///      manually sending some ether to the strategy
    receive() external payable {}
}
