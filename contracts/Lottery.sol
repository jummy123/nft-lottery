pragma solidity ^0.8.0;

import "OpenZeppelin/openzeppelin-contracts@4.3.3/contracts/token/ERC721/ERC721.sol";
import "OpenZeppelin/openzeppelin-contracts@4.3.3/contracts/access/Ownable.sol";

import "./Treasury.sol";


contract Lottery is ERC721 {

    // Counter for token IDs.
    uint256 public ticketCounter;

    // The price in AVAX per token.
    uint public ticketPrice = 1 ether;

    // Timestamp of the last draw that took place.
    uint public lastDrawTimestamp;

    // Minimum seconds between draws.
    uint public minSecondsBetweenDraw = 60 * 60 * 24;

    // Mapping storing when a ticket was minted.
    mapping(uint => uint) public ticketMintDate;

    // Mapping of ticket to array index
    mapping(uint => uint) public ticketIndex;

    // Array of all ticket eligible for draw, used for choosing a random
    // winner where random r, 0 <= r <= activeTickets.length
    uint[] public activeTickets;

    // The address for the treasury
    Treasury public treasury;

    constructor () ERC721 ("Lottery", "LD") {
        ticketCounter = 0;
        lastDrawTimestamp = block.timestamp;
        treasury = new Treasury();
    }

    /// @notice Buy a new ticker.
    /// @return The lottery number (and token ID).
    function purchase() public payable returns (uint256) {
        require(msg.value == ticketPrice);
        treasury.deposit{value: msg.value}();
        uint256 ticketId = ticketCounter;
        _safeMint(msg.sender, ticketId);

        ticketMintDate[ticketId] = block.timestamp;

        activeTickets.push(ticketId);
        uint idx = activeTickets.length;
        ticketIndex[ticketId] = idx;

        ticketCounter = ticketCounter + 1;
        return ticketId;
    }

    /// @notice Burn the ticket and refunds the cost price.
    function refund(uint256 ticketId) public {
        require(
            _isApprovedOrOwner(_msgSender(), ticketId),
            "ERC721Burnable: caller is not owner nor approved");
        require(_exists(ticketId), "token already burned or not minted");

        _burn(ticketId);

        uint idx = ticketIndex[ticketId];
        delete activeTickets[idx - 1];
        if (activeTickets.length > 1) {
            activeTickets[idx] = activeTickets[activeTickets.length - 1];
            activeTickets.pop();
            ticketIndex[ticketId] = 0;
            ticketIndex[activeTickets[idx]] = idx;
        }

        treasury.withdraw(msg.sender, ticketPrice);
    }

    /// @notice Is this ticket elibible for the next draw.
    function isEligible(uint ticketId) public view returns (bool) {
        if (!_exists(ticketId)) {
            return false;
        }
        // There is a special case if no draw has taken place yet all tickets
        // are eligible.
        if (lastDrawTimestamp == 0) {
            return true;
        }
        if (ticketMintDate[ticketId] > lastDrawTimestamp) {
            return false;
        }
        return true;
    }

    /// @notice Performs the daily draw.
    /// @return Returns the ID of the winning ticket.
    function draw() public returns (uint) {
        // There can be no draw if there are no active tickets.
        require(activeTickets.length > 0, "No active tickets for draw");
        lastDrawTimestamp = block.timestamp;
        /// XXX: Not safe, wait for VRF.
        uint winningTicketIdx = uint(keccak256(abi.encodePacked(block.timestamp))) % activeTickets.length;

        /// We need to look at the treasury to see what the prize is.
        return activeTickets[winningTicketIdx];
    }
}

