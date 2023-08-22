from unittest.mock import Mock

import pytest
from eth_account.messages import encode_defunct
from eth_hash.backends.pycryptodome import keccak256

import variables
from bots.pause import PauserBot


# https://goerli.etherscan.io/address/0xe57025E250275cA56f92d76660DEcfc490C7E79A#readContract#F12
DSM_OWNER = '0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1'


@pytest.fixture
def pause_bot(web3_lido_unit, block_data):
    web3_lido_unit.eth.get_block = Mock(return_value=block_data)
    variables.MESSAGE_TRANSPORTS = ''
    web3_lido_unit.lido.deposit_security_module.get_pause_intent_validity_period_blocks = Mock(return_value=10)
    yield PauserBot(web3_lido_unit)


@pytest.fixture
def pause_message():
    yield {
        "blockHash": "0xe41c0212516a899c455203e833903c802338daa3048bc637b623f6fba0a1685c",
        "blockNumber": 10,
        "guardianAddress": "0x3dc4cF780F2599B528F37dedB34449Fb65Ef7d4A",
        "guardianIndex": 0,
        "stakingModuleId": 1,
        "signature": {
            "_vs": "0xd4933925f5f97a9632b4b1bc621a1c2771d58eaf6eee27dcf915eac8af010537",
            "r": "0xbaa668505cd496caaf7117dd074338197200175057909ab73a04463656bdb0fa",
            "recoveryParam": 1,
            "s": "0x54933925f5f97a9632b4b1bc621a1c2771d58eaf6eee27dcf915eac8af010537",
            "v": 28
        },
        "type": "pause"
    }


@pytest.fixture
def add_account_to_guardian(web3_lido_integration, set_integration_account):
    web3_lido_integration.provider.make_request('hardhat_impersonateAccount', [DSM_OWNER])

    try:
        # If guardian removal failed
        web3_lido_integration.lido.deposit_security_module.functions.addGuardian(variables.ACCOUNT.address, 1).transact({'from': DSM_OWNER})
    except:
        pass

    yield web3_lido_integration

    web3_lido_integration.lido.deposit_security_module.functions.removeGuardian(variables.ACCOUNT.address, 1).transact({'from': DSM_OWNER})


@pytest.mark.unit
def test_pause_bot_without_messages(pause_bot, block_data):
    pause_bot.message_storage.get_messages = Mock(return_value=[])
    pause_bot._send_pause_message = Mock()
    pause_bot.execute(block_data)
    pause_bot._send_pause_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize(
    "block_range",
    [4, pytest.param(6, marks=pytest.mark.xfail)],
)
def test_pause_bot_outdate_messages(pause_bot, block_data, pause_message, block_range):
    pause_message['blockNumber'] = 5
    pause_bot.message_storage.messages = [pause_message]
    pause_bot.w3.lido.deposit_security_module.get_pause_intent_validity_period_blocks = Mock(return_value=block_range)

    pause_bot._send_pause_message = Mock()
    pause_bot.execute(block_data)
    pause_bot._send_pause_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize(
    "active_module",
    [False, pytest.param(True, marks=pytest.mark.xfail)],
)
def test_pause_bot_clean_messages(pause_bot, block_data, pause_message, active_module):
    pause_bot.message_storage.messages = [pause_message]
    pause_bot.w3.lido.staking_router.is_staking_module_active = Mock(return_value=active_module)

    pause_bot.execute(block_data)
    assert len(pause_bot.message_storage.messages) == 0


@pytest.mark.unit
def test_pause_message_filtered_by_module_id(pause_bot, block_data, pause_message):
    new_message = pause_message.copy()
    new_message['stakingModuleId'] = 2

    pause_bot.message_storage.messages = [pause_message, pause_message, new_message]
    pause_bot.w3.lido.staking_router.is_staking_module_active = lambda module_id: not module_id % 2

    pause_bot.execute(block_data)

    # Only module_id=1 messages filtered
    assert len(pause_bot.message_storage.messages) == 1


@pytest.mark.integration
def test_pauser_bot(web3_lido_integration, add_account_to_guardian):
    latest = web3_lido_integration.eth.get_block('latest')

    prefix = web3_lido_integration.lido.deposit_security_module.get_attest_message_prefix()
    block_number = latest.number.to_bytes(32, 'big')
    staking_module_id = int(1).to_bytes(32, 'big')

    k = keccak256(prefix + block_number + staking_module_id)
    msg = encode_defunct(k)
    signed = web3_lido_integration.eth.account.sign_message(msg, private_key=variables.ACCOUNT.privateKey)

    pm = {
        "blockHash": latest.hash.hex(),
        "blockNumber": latest.number,
        "guardianAddress": variables.ACCOUNT.address,
        "stakingModuleId": 1,
        "signature": {
            "r": hex(signed.r),
            "s": hex(signed.s),
            "v": 28
        },
        "type": "pause"
    }

    pb = PauserBot(web3_lido_integration)
    pb.execute(latest)

    # Check no pause
    assert not web3_lido_integration.lido.staking_router.is_staking_module_deposits_paused(1)

    # Add pause message
    pb.message_storage.messages = [pm]
    pb.execute(latest)

    # Check there is pause message and module paused
    assert web3_lido_integration.lido.staking_router.is_staking_module_deposits_paused(1)
    assert len(pb.message_storage.messages) == 1

    pb.execute(latest)
    # Check pause message cleaned
    assert not pb.message_storage.messages

    # Cleanup
    web3_lido_integration.lido.deposit_security_module.functions.unpauseDeposits(pm['stakingModuleId']).transact({'from': DSM_OWNER})
    assert not web3_lido_integration.lido.staking_router.is_staking_module_deposits_paused(1)
