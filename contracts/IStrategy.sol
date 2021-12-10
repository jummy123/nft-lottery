pragma solidity ^0.8.0;


interface IStrategy {
    function invest() external payable;
    function withdraw(uint amount) external;
    function balanceOfUnderlying() external view returns (uint);
}
