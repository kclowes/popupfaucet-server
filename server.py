from flask import Flask, request, jsonify

from web3 import HTTPProvider, Web3, EthereumTesterProvider
import os
import time
import json

app = Flask(__name__)

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# Initialize Web3
w3_tester = Web3(EthereumTesterProvider())
w3_op_sepolia = Web3(HTTPProvider(os.getenv('RPC_URL')))

# Deployments:
ADMIN_PK = os.getenv("POPUPFAUCET_ADMIN_PK")
DEPLOY_OP_SEPOLIA = "0xc5cDa98Ac108f97cA7971311267d0E7b08A6Fd44"
DEPLOY_BASE_SEPOLIA = ""
DEPLOY_SEPOLIA = ""


with open("artifacts.json") as f:
    artifacts = json.load(f)

# for local (eth-tester) testing:
if DEV_MODE:
    w3 = w3_tester
    admin_account = w3.eth.accounts[0]
    contract_factory = w3.eth.contract(
        abi=artifacts["abi"], bytecode=artifacts["deploymentBytecode"]["bytecode"]
    )
    tx_hash = contract_factory.constructor(admin_account).transact(
        {"from": admin_account}
    )
    contract = w3.eth.contract(
        address=w3.eth.get_transaction_receipt(tx_hash)["contractAddress"],
        abi=artifacts["abi"],
    )
else:
    w3 = w3_op_sepolia
    contract = w3.eth.contract(
        address=DEPLOY_OP_SEPOLIA,
        abi=artifacts["abi"],
    )
    admin_account = w3.eth.account.from_key(ADMIN_PK)

# Check connection
if not w3.is_connected():
    raise ConnectionError("Failed to connect to the network")


@app.route("/availability", methods=["GET"])
def check_availability():
    event_code = request.args.get("event_code")
    if not event_code:
        return jsonify({"error": "event_code parameter is required"}), 400

    try:
        is_available = contract.functions.eventNameAvailable(event_code).call()
        return jsonify({"event_code": event_code, "is_available": is_available}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/status", methods=["GET"])
def check_status():
    event_code = request.args.get("event_code")
    if not event_code:
        return jsonify({"error": "event_code parameter is required"}), 400
    w3 = w3_op_sepolia
    if DEV_MODE:
        w3 = w3_tester
    try:
        event_name_unclaimed = contract.functions.eventNameAvailable(event_code).call()
        print(f"event_name_unclaimed: {event_name_unclaimed}")
        if event_name_unclaimed:
            return jsonify({"event_exists": False, "available_ether": 0}), 200

        funds_available = contract.functions.eventFundsAvailable(event_code).call()
        print(f"funds_available: {funds_available}")
        ether_in_wei = w3.from_wei(funds_available, "ether")
        return jsonify({"event_exists": True, "available_ether": ether_in_wei}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/seeder-funded", methods=["POST"])
def check_seeder_funded():
    data = request.json
    pk = data.get("pk")
    w3 = w3_op_sepolia
    if DEV_MODE:
        w3 = w3_tester
    acct = w3.eth.account.from_key(pk)

    if DEV_MODE:
        # mock transfer
        w3.eth.send_transaction(
            {
                "from": w3.eth.accounts[1],
                "to": acct.address,
                "value": w3.to_wei("1", "ether"),
            }
        )

    # Convert ether amount to Wei
    wei_amount = w3.eth.get_balance(acct.address)
    print(f"wei_amount: {wei_amount}")

    if wei_amount == 0:
        return jsonify({"error": "Insufficient balance"}), 400
    else:
        return jsonify({"balance": wei_amount}), 200


@app.route("/create-faucet", methods=["POST"])
def create_faucet():
    data = request.json
    event_code = data.get("event_code")
    pk = data.get("pk")
    # network = data.get("network")
    w3 = w3_op_sepolia
    if DEV_MODE:
        w3 = w3_tester
    acct = w3.eth.account.from_key(pk)

    if not event_code:
        return jsonify({"error": "Event code is required"}), 400

    try:
        gas_limit = 74338
        # gas_limit = contract.functions.seedFunds(event_code).estimate_gas( {"type": 2, "from": acct.address, "value": 1}
        # )
        # gas_price = w3.to_wei("0.2", "gwei")
        # gas_cost = gas_limit * gas_price
        value = int(w3.eth.get_balance(acct.address) * 0.9)
        tx_params = {
            "type": 2,
            "nonce": 0,
            "gas": gas_limit,
            "value": value,
            "maxPriorityFeePerGas": 1000,
            "maxFeePerGas": 1000,
        }

        tx = contract.functions.seedFunds(event_code).build_transaction(tx_params)
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        # TODO: anything leftover? send to admin

        return jsonify({"tx_receipt": tx_receipt["transactionHash"]}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


@app.route("/top-up-faucet", methods=["POST"])
def top_up_faucet():
    data = request.json
    event_code = data.get("event_code")
    ether_amount = data.get("ether_amount")

    if not event_code or not ether_amount:
        return jsonify({"error": "Event code and ether amount are required"}), 400

    try:
        # Encode event code
        # encoded_event_code = w3.solidityKeccak(['string'], [event_code]).hex()

        # Convert ether amount to Wei
        # wei_amount = w3.toWei(ether_amount, 'ether')

        # Build transaction
        # tx = contract.functions.topUpFaucet(encoded_event_code).buildTransaction({
        #     'chainId': 1,  # Mainnet
        #     'gas': 2000000,
        #     'gasPrice': w3.toWei('50', 'gwei'),
        #     'nonce': w3.eth.getTransactionCount(wallet_address),
        #     'value': wei_amount,
        # })

        # Sign transaction
        # signed_tx = w3.eth.account.signTransaction(tx, private_key=private_key)

        # Send transaction
        # tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)

        # Mock transaction hash
        tx_hash = "0xabcdef1234567890"
        return jsonify({"tx_hash": tx_hash}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/claim-faucet", methods=["POST"])
def claim_faucet():
    data = request.json
    event_code = data.get("event_code")
    address = data.get("address")
    w3 = w3_op_sepolia
    if DEV_MODE:
        w3 = w3_tester

    if not event_code:
        return jsonify({"error": "Event code is required"}), 400
    if not address:
        return jsonify({"error": "Address is required"}), 400

    try:
        gas_limit = contract.functions.drip(address, event_code).estimate_gas(
            {"from": admin_account}
        )
        tx = contract.functions.seedFunds(event_code).build_transaction(
            {
                "nonce": w3.eth.get_transaction_count(admin_account),
            }
        )

        if DEV_MODE:
            # eth-tester
            tx_hash = w3.eth.send_transaction(tx)
        else:
            signed_tx = w3.eth.account.sign_transaction(
                tx, private_key=admin_account.key
            )
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return jsonify({"tx_hash": tx_receipt["transactionHash"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
