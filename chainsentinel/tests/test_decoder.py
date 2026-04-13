import pytest


def test_decoder_decodes_erc20_transfer(sample_raw_log, sample_erc20_abi):
    from pipeline.decoder import Decoder

    decoder = Decoder(abis={"standards": [sample_erc20_abi]})
    result = decoder.decode_log(sample_raw_log)

    assert result["event_name"] == "Transfer"
    assert result["decode_status"] == "decoded"
    assert "from" in result["event_args"]
    assert "to" in result["event_args"]
    assert "value" in result["event_args"]


def test_decoder_returns_unknown_for_unrecognized_log():
    from pipeline.decoder import Decoder

    decoder = Decoder(abis={"standards": []})
    unknown_log = {
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "topics": ["0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"],
        "data": "0x00000000000000000000000000000000000000000000000000000000000000ff",
    }
    result = decoder.decode_log(unknown_log)

    assert result["decode_status"] == "unknown"
    assert result["event_name"] is None
    assert result["topics"] == unknown_log["topics"]


def test_decoder_decodes_function_selector():
    from pipeline.decoder import Decoder

    decoder = Decoder(abis={"standards": [[
        {
            "inputs": [
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function",
        }
    ]]})

    # transfer(address,uint256) selector = 0xa9059cbb
    result = decoder.decode_function_input(
        "0xa9059cbb"
        "000000000000000000000000deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
        "0000000000000000000000000000000000000000000000000000000005f5e100"
    )

    assert result["function_name"] == "transfer"
    assert result["decode_status"] == "decoded"


def test_decoder_updates_selector_registry():
    from pipeline.decoder import Decoder

    decoder = Decoder(abis={"standards": [[
        {
            "inputs": [
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function",
        }
    ]]})

    assert "0xa9059cbb" in decoder.selector_map
    assert decoder.selector_map["0xa9059cbb"]["name"] == "transfer"
