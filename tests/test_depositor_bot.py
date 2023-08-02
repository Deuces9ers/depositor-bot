import logging
from unittest.mock import Mock

from blockchain.contracts import contracts
from bots.depositor_bot import DepositorBot
from utils.logs import find_log_message
from fixtures.pytest_mocks import *


ISSUES_FOUND_LOG = 'Issues found.'
ISSUES_NOT_FOUND_LOG = 'No issues found.'


def test_deposit_issues__account_balance(
    caplog,
    setup_web3_deposit_fixtures_small_balance,
    remove_sleep,
    remove_transport,
    setup_ping_message_to_kafka,
    setup_deposit_message_to_kafka,
    setup_account,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures_small_balance)
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures_small_balance)
    depositor_bot._get_nonce = Mock(return_value=1)
    depositor_bot.run_cycle()

    assert find_log_message(caplog, depositor_bot.NOT_ENOUGH_BALANCE_ON_ACCOUNT)
    record = find_log_message(caplog, ISSUES_FOUND_LOG)
    assert record
    assert record.msg['value'] == [depositor_bot.NOT_ENOUGH_BALANCE_ON_ACCOUNT]
    assert not find_log_message(caplog, ISSUES_NOT_FOUND_LOG)


def test_deposit_issues__gas_strategy(
    caplog,
    setup_web3_deposit_fixtures_with_high_gas,
    remove_sleep,
    remove_transport,
    setup_ping_message_to_kafka,
    setup_deposit_message_to_kafka,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures_with_high_gas)
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures_with_high_gas)
    depositor_bot._get_nonce = Mock(return_value=1)
    depositor_bot.run_cycle()

    assert find_log_message(caplog, depositor_bot.GAS_FEE_HIGHER_THAN_RECOMMENDED)
    record = find_log_message(caplog, ISSUES_FOUND_LOG)
    assert record
    assert record.msg['value'] == [depositor_bot.GAS_FEE_HIGHER_THAN_RECOMMENDED]
    assert not find_log_message(caplog, ISSUES_NOT_FOUND_LOG)


def test_deposit_issues__security_check(
    caplog,
    setup_web3_deposit_fixtures_prohibits_the_deposit,
    remove_sleep,
    remove_transport,
    setup_ping_message_to_kafka,
    setup_deposit_message_to_kafka,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures_prohibits_the_deposit)
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures_prohibits_the_deposit)
    depositor_bot._get_nonce = Mock(return_value=1)
    depositor_bot.run_cycle()

    assert find_log_message(caplog, depositor_bot.DEPOSIT_SECURITY_ISSUE)
    record = find_log_message(caplog, ISSUES_FOUND_LOG)
    assert record
    assert record.msg['value'] == [depositor_bot.DEPOSIT_SECURITY_ISSUE]
    assert not find_log_message(caplog, ISSUES_NOT_FOUND_LOG)


def test_deposit_issues__buffered_ether(
    caplog,
    setup_web3_deposit_fixtures_not_enough_buffered_ether,
    remove_sleep,
    remove_transport,
    setup_ping_message_to_kafka,
    setup_deposit_message_to_kafka,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures_not_enough_buffered_ether)
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures_not_enough_buffered_ether)
    depositor_bot._get_nonce = Mock(return_value=1)
    depositor_bot.run_cycle()

    assert find_log_message(caplog, depositor_bot.LIDO_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_ETHER)
    record = find_log_message(caplog, ISSUES_FOUND_LOG)
    assert record
    assert record.msg['value'] == [depositor_bot.LIDO_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_ETHER]
    assert not find_log_message(caplog, ISSUES_NOT_FOUND_LOG)


def test_deposit_issues__enough_signs(
    caplog,
    setup_web3_deposit_fixtures,
    remove_sleep,
    remove_transport,
    setup_ping_message_to_kafka,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures)
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures)
    depositor_bot._get_nonce = Mock(return_value=1)
    depositor_bot.run_cycle()

    assert find_log_message(caplog, depositor_bot.QUORUM_IS_NOT_READY)
    record = find_log_message(caplog, ISSUES_FOUND_LOG)
    assert record
    assert record.msg['value'] == [depositor_bot.QUORUM_IS_NOT_READY]
    assert not find_log_message(caplog, ISSUES_NOT_FOUND_LOG)


def test_deposit_issues__no_free_keys(
    caplog,
    setup_web3_deposit_fixtures_no_free_keys,
    remove_sleep,
    remove_transport,
    setup_ping_message_to_kafka,
    setup_deposit_message_to_kafka,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures_no_free_keys)
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures_no_free_keys)
    depositor_bot._get_nonce = Mock(return_value=1)
    depositor_bot.run_cycle()

    assert find_log_message(caplog, depositor_bot.DEPOSITOR_CAN_DEPOSIT_KEYS)
    record = find_log_message(caplog, ISSUES_FOUND_LOG)
    assert record
    assert record.msg['value'] == [depositor_bot.DEPOSITOR_CAN_DEPOSIT_KEYS]
    assert not find_log_message(caplog, ISSUES_NOT_FOUND_LOG)


def test_depositor_bot__no_account(
    caplog,
    setup_web3_deposit_fixtures,
    setup_deposit_message_to_kafka,
    remove_sleep,
    remove_transport,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures)
    contracts.deposit_security_module.functions.depositBufferedEther = Mock()
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures)
    depositor_bot._get_nonce = Mock(return_value=1)
    depositor_bot.run_cycle()

    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, ISSUES_NOT_FOUND_LOG)
    assert find_log_message(caplog, 'Deposit local call succeed.')
    assert find_log_message(caplog, 'Account was not provided.')


def test_depositor_bot__no_create_tx(
    caplog,
    setup_web3_deposit_fixtures,
    setup_deposit_message_to_kafka,
    setup_account,
    remove_sleep,
    remove_transport,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures)
    contracts.deposit_security_module.functions.depositBufferedEther = Mock()
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures)
    depositor_bot._get_nonce = Mock(return_value=1)
    depositor_bot.run_cycle()

    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, ISSUES_NOT_FOUND_LOG)
    assert find_log_message(caplog, 'Deposit local call succeed.')
    assert find_log_message(caplog, 'Run in dry mode.')


def test_depositor_bot__deposit(
    caplog,
    setup_web3_deposit_fixtures,
    setup_ping_message_to_kafka,
    setup_deposit_message_to_kafka,
    setup_account,
    setup_flashbots,
    setup_create_txs,
    remove_sleep,
    remove_transport,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures)
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures)
    depositor_bot.w3.eth.get_transaction_count = Mock(return_value=1)
    depositor_bot.w3.flashbots = Mock(return_value=True)
    depositor_bot._check_transaction = Mock(return_value=True)
    depositor_bot._get_nonce = Mock(return_value=1)

    try:
        depositor_bot.run_cycle()
    except TypeError:
        # Mining transaction error expected. Can't mock it correctly. Just check logs.
        pass

    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, ISSUES_NOT_FOUND_LOG)
    assert find_log_message(caplog, 'Sending deposit transaction.')
    assert find_log_message(caplog, 'Try to deposit. Flashbots mode.')


def test_depositor_bot__deposit_classic(
    caplog,
    setup_web3_deposit_fixtures,
    setup_ping_message_to_kafka,
    setup_deposit_message_to_kafka,
    setup_account,
    setup_flashbots,
    setup_create_txs,
    remove_sleep,
    remove_transport,
):
    caplog.set_level(logging.INFO)
    contracts.initialize(setup_web3_deposit_fixtures)
    depositor_bot = DepositorBot(setup_web3_deposit_fixtures)
    depositor_bot.last_fb_deposit_failed = True
    depositor_bot.w3.eth.get_transaction_count = Mock(return_value=1)
    depositor_bot._check_transaction = Mock(return_value=True)
    depositor_bot._get_nonce = Mock(return_value=1)

    depositor_bot.run_cycle()

    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, ISSUES_NOT_FOUND_LOG)
    assert find_log_message(caplog, 'Sending deposit transaction.')
    assert find_log_message(caplog, 'Try to deposit. Classic mode.')
