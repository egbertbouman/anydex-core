from __future__ import absolute_import

from twisted.internet.defer import DeferredList
from twisted.web import http, resource
from twisted.web.server import NOT_DONE_YET

import anydex.util.json_util as json
from anydex.restapi.base_market_endpoint import BaseMarketEndpoint


class WalletsEndpoint(BaseMarketEndpoint):
    """
    This class represents the root endpoint of the wallets resource.
    """

    def __init__(self, session):
        BaseMarketEndpoint.__init__(self, session)
        self.session = session

    def render_GET(self, request):
        """
        .. http:get:: /wallets

        A GET request to this endpoint will return information about all available wallets in Tribler.
        This includes information about the address, a human-readable wallet name and the balance.

            **Example request**:

            .. sourcecode:: none

                curl -X GET http://localhost:8085/wallets

            **Example response**:

            .. sourcecode:: javascript

                {
                    "wallets": [{
                        "created": True,
                        "name": "Bitcoin",
                        "unlocked": True,
                        "precision": 8,
                        "min_unit": 100000,
                        "address": "17AVS7n3zgBjPq1JT4uVmEXdcX3vgB2wAh",
                        "balance": {
                            "available": 0.000126,
                            "pending": 0.0,
                            "currency": "BTC"
                        }
                    }, ...]
                }
        """
        wallets = {}
        balance_deferreds = []
        for wallet_id, wallet in self.get_market_community().wallets.items():
            wallets[wallet_id] = {
                'created': wallet.created,
                'unlocked': wallet.unlocked,
                'address': wallet.get_address(),
                'name': wallet.get_name(),
                'precision': wallet.precision(),
                'min_unit': wallet.min_unit()
            }
            balance_deferreds.append(wallet.get_balance().addCallback(
                lambda balance, wid=wallet_id: (wid, balance)))

        def on_received_balances(balances):
            for _, balance_info in balances:
                wallets[balance_info[0]]['balance'] = balance_info[1]

            request.write(json.twisted_dumps({"wallets": wallets}))
            request.finish()

        balance_deferred_list = DeferredList(balance_deferreds)
        balance_deferred_list.addCallback(on_received_balances)

        return NOT_DONE_YET

    def getChild(self, path, request):
        return WalletEndpoint(self.session, path)


class WalletEndpoint(BaseMarketEndpoint):
    """
    This class represents the endpoint for a single wallet.
    """
    def __init__(self, session, identifier):
        BaseMarketEndpoint.__init__(self, session)
        self.session = session
        self.identifier = identifier.upper().decode('utf-8')

        child_handler_dict = {
            b"balance": WalletBalanceEndpoint,
            b"transactions": WalletTransactionsEndpoint,
            b"transfer": WalletTransferEndpoint
        }
        for path, child_cls in child_handler_dict.items():
            self.putChild(path, child_cls(self.session, self.identifier))

    def render_PUT(self, request):
        """
        .. http:put:: /wallets/(string:wallet identifier)

        A request to this endpoint will create a new wallet.

            **Example request**:

            .. sourcecode:: none

                curl -X PUT http://localhost:8085/wallets/BTC

            **Example response**:

            .. sourcecode:: javascript

                {
                    "created": True
                }
        """
        if self.get_market_community().wallets[self.identifier].created:
            request.setResponseCode(http.BAD_REQUEST)
            return json.twisted_dumps({"error": "this wallet already exists"})

        def on_wallet_created(_):
            request.write(json.twisted_dumps({"created": True}))
            request.finish()

        def on_create_error(error):
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.write(json.twisted_dumps({"error": error.getErrorMessage()}))
            request.finish()

        self.get_market_community().wallets[self.identifier].create_wallet()\
            .addCallbacks(on_wallet_created, on_create_error)

        return NOT_DONE_YET


class WalletBalanceEndpoint(BaseMarketEndpoint):
    """
    This class handles requests regarding the balance in a wallet.
    """

    def __init__(self, session, identifier):
        BaseMarketEndpoint.__init__(self, session)
        self.session = session
        self.identifier = identifier

    def render_GET(self, request):
        """
        .. http:get:: /wallets/(string:wallet identifier)/balance

        A GET request to this endpoint will return balance information of a specific wallet.

            **Example request**:

            .. sourcecode:: none

                curl -X GET http://localhost:8085/wallets/BTC/balance

            **Example response**:

            .. sourcecode:: javascript

                {
                    "balance": {
                        "available": 0.000126,
                        "pending": 0.0,
                        "currency": "BTC"
                    }
                }
        """
        def on_balance(balance):
            request.write(json.twisted_dumps({"balance": balance}))
            request.finish()

        self.get_market_community().wallets[self.identifier].get_balance().addCallback(on_balance)

        return NOT_DONE_YET


class WalletTransactionsEndpoint(BaseMarketEndpoint):
    """
    This class handles requests regarding the transactions of a wallet.
    """

    def __init__(self, session, identifier):
        BaseMarketEndpoint.__init__(self, session)
        self.session = session
        self.identifier = identifier

    def render_GET(self, request):
        """
        .. http:get:: /wallets/(string:wallet identifier)/transactions

        A GET request to this endpoint will return past transactions of a specific wallet.

            **Example request**:

            .. sourcecode:: none

                curl -X GET http://localhost:8085/wallets/BTC/transactions

            **Example response**:

            .. sourcecode:: javascript

                {
                    "transactions": [{
                        "currency": "BTC",
                        "to": "17AVS7n3zgBjPq1JT4uVmEXdcX3vgB2wAh",
                        "outgoing": false,
                        "from": "",
                        "description": "",
                        "timestamp": "1489673696",
                        "fee_amount": 0.0,
                        "amount": 0.00395598,
                        "id": "6f6c40d034d69c5113ad8cb3710c172955f84787b9313ede1c39cac85eeaaffe"
                    }, ...]
                }
        """
        def on_transactions(transactions):
            request.write(json.twisted_dumps({"transactions": transactions}))
            request.finish()

        self.get_market_community().wallets[self.identifier].get_transactions().addCallback(on_transactions)

        return NOT_DONE_YET


class WalletTransferEndpoint(BaseMarketEndpoint):
    """
    This class handles requests regarding transferring money by a wallet.
    """

    def __init__(self, session, identifier):
        BaseMarketEndpoint.__init__(self, session)
        self.session = session
        self.identifier = identifier

    def render_POST(self, request):
        """
        .. http:post:: /wallets/(string:wallet identifier)/transfer

        A POST request to this endpoint will transfer some units from a wallet to another address.

            **Example request**:

            .. sourcecode:: none

                curl -X POST http://localhost:8085/wallets/BTC/transfer
                --data "amount=0.3&destination=mpC1DDgSP4PKc5HxJzQ5w9q6CGLBEQuLsN"

            **Example response**:

            .. sourcecode:: javascript

                {
                    "txid": "abcd"
                }
        """
        parameters = http.parse_qs(request.content.read(), 1)

        if self.identifier != "BTC" and self.identifier != "TBTC":
            request.setResponseCode(http.BAD_REQUEST)
            return json.twisted_dumps({"error": "currently, currency transfers using the API "
                                                "is only supported for Bitcoin"})

        wallet = self.get_market_community().wallets[self.identifier]

        if not wallet.created:
            request.setResponseCode(http.BAD_REQUEST)
            return json.twisted_dumps({"error": "this wallet is not created"})

        if b'amount' not in parameters or b'destination' not in parameters:
            request.setResponseCode(http.BAD_REQUEST)
            return json.twisted_dumps({"error": "an amount and a destination address are required"})

        def on_transferred(txid):
            request.write(json.twisted_dumps({"txid": txid}))
            request.finish()

        def on_transfer_error(error):
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.write(json.twisted_dumps({"txid": "", "error": error.getErrorMessage()}))
            request.finish()

        wallet.transfer(parameters[b'amount'][0], parameters[b'destination'][0]).addCallback(on_transferred)\
            .addErrback(on_transfer_error)

        return NOT_DONE_YET
