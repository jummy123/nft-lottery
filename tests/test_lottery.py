import pytest

from brownie import (
    accounts,
    reverts,
    Wei,
    Lottery,
    Treasury,
    DummyStrategy,
    chain,
)


@pytest.fixture
def lottery():
    """
    Return a deployed `Lottery` contract with owner
    of `accounts[0]`.
    """
    return Lottery.deploy({'from': accounts[0]})


@pytest.fixture
def treasury():
    return Treasury.deploy({'from': accounts[0]})


@pytest.fixture
def dummy_strategy():
    return DummyStrategy.deploy({'from': accounts[0]})


@pytest.fixture
def lottery_dummy_strategy():
    """
    Return a lottery instantiated with a treasury and a dummy strategy.
    """
    lottery = Lottery.deploy({'from': accounts[0]})

    treasury = Treasury.at(lottery.treasury.call())

    strategy = DummyStrategy.deploy({'from': accounts[0]})
    strategy.transferOwnership(treasury.address, {'from': accounts[0]})

    treasury.setStrategy(strategy.address, {'from': accounts[0]})

    return lottery


def test_purchase_no_ether(lottery):
    with reverts():
        lottery.purchase({'from': accounts[0]})


def test_purchase_too_little_ether(lottery):
    with reverts():
        lottery.purchase({'from': accounts[0], 'value': Wei('0.99 ether')})


def test_purchase_too_much_ether(lottery):
    with reverts():
        lottery.purchase({'from': accounts[0], 'value': Wei('2 ether')})


def test_purchase_and_ownership(lottery):
    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticket = tx.return_value
    assert lottery.balanceOf(accounts[0].address) == 1
    assert lottery.ownerOf(ticket) == accounts[0].address


def test_refund_not_owner(lottery):
    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticket = tx.return_value
    with reverts():
        lottery.refund(ticket, {'from': accounts[1]})


def test_refund(lottery):
    start_balance = accounts[0].balance()

    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticket = tx.return_value
    assert accounts[0].balance() == start_balance - Wei('1 ether')

    lottery.refund(ticket, {'from': accounts[0]})
    assert accounts[0].balance() == start_balance


def test_refund_burned_token(lottery):
    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    lottery.refund(tx.return_value, {'from': accounts[0]})
    with reverts():
        lottery.refund(tx.return_value, {'from': accounts[0]})


def test_refund_not_minted(lottery):
    with reverts():
        lottery.refund(0, {'from': accounts[0]})


def test_withdraw_treasury_not_owner(treasury):
    with reverts():
        treasury.withdraw(accounts[1].address, Wei("0.5 ether"), {'from': accounts[1]})


def test_withdraw_treasury(treasury):
    treasury.deposit({'from': accounts[0], 'value': Wei('1 ether')})
    start_balance = accounts[1].balance()
    treasury.withdraw(accounts[1].address, Wei("0.5 ether"), {'from': accounts[0]})
    assert accounts[1].balance() == start_balance + Wei('0.5 ether')


def test_withdraw_treasury_no_funds(treasury):
    with reverts():
        treasury.withdraw(accounts[0].address, Wei("0.5 ether"), {'from': accounts[0]})


def test_new_mint_eligible_for_first_draw(lottery):
    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticketId = tx.return_value
    assert lottery.isEligible(ticketId) is True


def test_new_mint_not_eligible_for_draw(lottery):
    lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    lottery.draw({'from': accounts[0]})
    chain.mine(blocks=1, timedelta=60)
    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticketId = tx.return_value
    assert lottery.isEligible(ticketId) is False


def test_redeemed_token_not_elible_for_draw(lottery):
    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticketId = tx.return_value
    lottery.draw({'from': accounts[0]})
    chain.mine(blocks=1, timedelta=60)
    lottery.refund(ticketId, {'from': accounts[0]})
    assert lottery.isEligible(ticketId) is False


def test_draw_reverts_if_no_tickets(lottery):
    with reverts():
        lottery.draw({'from': accounts[0]})


def test_only_one_ticket_must_win(lottery):
    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticketId = tx.return_value
    tx = lottery.draw({'from': accounts[0]})
    assert tx.return_value == ticketId


def test_one_of_two_tickets_must_win(lottery):
    ticket1, ticket2 = (
        lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')}).return_value,
        lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')}).return_value,
    )
    tx = lottery.draw({'from': accounts[0]})
    assert tx.return_value in (ticket1, ticket2)


def test_cant_call_winnings_if_not_owner(lottery):
    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticketId = tx.return_value
    treasury = Treasury.at(lottery.treasury.call())
    with reverts():
        treasury.withdrawWinnings(ticketId, {'from': accounts[1]})


def test_cant_call_winnings_if_balance_0(lottery):
    tx = lottery.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticketId = tx.return_value
    treasury = Treasury.at(lottery.treasury.call())
    with reverts():
        treasury.withdrawWinnings(ticketId, {'from': accounts[0]})


@pytest.mark.skip('Needs governance')
def test_treasury_set_strategy_not_owner(treasury, dummy_strategy):
    with reverts():
        treasury.setStrategy(dummy_strategy.address, {'from': accounts[1]})


def test_treasury_set_strategy(treasury, dummy_strategy):
    treasury.setStrategy(dummy_strategy.address, {'from': accounts[0]})
    assert treasury.strategy.call() == dummy_strategy.address


def test_current_prize_no_tickets(lottery_dummy_strategy):
    treasury = Treasury.at(lottery_dummy_strategy.treasury.call())
    assert treasury.currentPrize() == 0


def test_current_prize_no_yield(lottery_dummy_strategy):
    lottery_dummy_strategy.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    treasury = Treasury.at(lottery_dummy_strategy.treasury.call())
    assert treasury.currentPrize() == 0


def test_current_prize_fake_yield(lottery_dummy_strategy):
    # Our contracts.
    lottery_dummy_strategy.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    treasury = Treasury.at(lottery_dummy_strategy.treasury.call())
    strategy = DummyStrategy.at(treasury.strategy.call())

    # Mint some tickets.
    lottery_dummy_strategy.purchase({'from': accounts[0], 'value': Wei('1 ether')})

    # Send some funds to the dummy strategy to simulate yield.
    accounts[0].transfer(strategy.address, 1234567)

    assert treasury.currentPrize() == 1234567


def test_withdraw_with_strategy(lottery_dummy_strategy):
    tx = lottery_dummy_strategy.purchase({'from': accounts[0], 'value': Wei('1 ether')})
    ticketId = tx.return_value
    lottery_dummy_strategy.refund(ticketId, {'from': accounts[0]})


def test_dummy_strategy_withdraw(dummy_strategy):
    start_balance = accounts[0].balance()
    dummy_strategy.invest({'from': accounts[0], 'value': '1 ether'})
    dummy_strategy.withdraw(Wei('1 ether'), {'from': accounts[0]})
    assert accounts[0].balance() == start_balance
