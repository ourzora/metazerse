from typing import Optional, Any

from eth_abi import encode as encode_abi, decode as decode_abi  # type: ignore[attr-defined]
from eth_utils import to_hex  # type: ignore[attr-defined]

from offchain.concurrency import parmap
from offchain.web3.contract_utils import function_signature_to_sighash
from offchain.web3.jsonrpc import EthereumJSONRPC

CHUNK_SIZE = 500


class ContractCaller:
    def __init__(self, rpc: Optional[EthereumJSONRPC] = None) -> None:
        self.rpc = rpc or EthereumJSONRPC()

    def single_address_single_fn_many_args(  # type: ignore[no-untyped-def]
        self,
        address: str,
        function_sig: str,
        return_type: list[str],
        args: list[list[Any]],
        block_tag: Optional[str] = "latest",
        chunk_size: int = CHUNK_SIZE,
        **kwargs,
    ) -> list[Optional[Any]]:
        """Call a single function on a single address with many different permutations of arguments

        Args:
            address (str): address to call function on
            function_sig (str): function signature (ex: "totalSupply()")
            return_type (list[str]): return function signature (ex: ["uint256"])
            args (list[list[Any]]): list of arguments passed in each fn call (ex: [[1], [2], [3]])
            chunk_size (int, optional): number of calls to group in a single req. Defaults to 500.

        Returns:
            list[Optional[Any]]: list of returned values, mapped 1-1 with args
        """  # noqa: E501

        req_params = [
            self.request_builder(address, function_sig, args[i], block_tag, **kwargs)
            for i in range(len(args))  # noqa: E501
        ]
        res = self._call_batch_chunked(req_params, chunk_size)
        return list(map(lambda r: self.decode_response(r, return_type), res))

    def single_address_many_fns_many_args(
        self,
        address: str,
        function_sigs: list[str],
        return_types: list[list[str]],
        args: list[list[Any]],
        block_tag: Optional[str] = "latest",
        chunk_size: int = CHUNK_SIZE,
    ) -> dict[str, Optional[Any]]:
        """Call many functions on a single addresses with different arguments per function

        Args:
            address (str): address to call function on
            function_sigs (list[str]): list of fn signature (ex: ["totalSupply()", "symbol()"])
            return_types (list[list[str]]): list of return function signature (ex: [["uint256"]])
            args (list[list[Any]]): list of arguments passed in each fn call (ex: [[1], [2], [3]])
            chunk_size (int, optional): [description]. Defaults to 500.

        Returns:
            dict[str, Optional[Any]]: dicts with fn names as keys (ex: {"totalSupply()": 1234})
        """  # noqa: E501
        assert len(function_sigs) == len(args) and len(args) == len(
            return_types
        ), "function names, return types, args must all be the same length"
        req_params = [
            self.request_builder(address, function_sigs[i], args[i], block_tag)
            for i in range(len(args))
        ]  # noqa: E501
        res = self._call_batch_chunked(req_params, chunk_size)
        cleaned = list(
            map(
                lambda i: self.decode_response(res[i], return_types[i]), range(len(res))
            )
        )  # noqa: E501
        return {k: v for k, v in zip(function_sigs, cleaned)}

    def _call_batch_chunked(
        self, request_params: list[list[Any]], chunk_size: int = CHUNK_SIZE
    ) -> list[Any]:  # noqa: E501
        """Perform concurrent batched requests by splitting a large batch into smaller chunks

        Args:
            request_params (list[list[Any]]): list of request parameters
            chunk_size (int, optional): size at which to split requests. Defaults to 500.

        Returns:
            list[Any]: merged list of all data from the many requests
        """  # noqa: E501

        def call(params: list[list[Any]]) -> list[Any]:
            return self.rpc.call_batch_chunked("eth_call", params)

        size = len(request_params)
        if size < chunk_size:
            return call(request_params)

        prev_offset, curr_offest = 0, chunk_size

        chunks = []
        while prev_offset < size:
            chunks.append(request_params[prev_offset:curr_offest])
            prev_offset = curr_offest
            curr_offest = min(curr_offest + chunk_size, size)

        results = parmap(call, chunks)
        return [i for res in results for i in res]

    def request_builder(  # type: ignore[no-untyped-def]
        self,
        address: str,
        function_sig: str,
        args: Optional[list] = None,  # type: ignore[type-arg]
        block_tag: Optional[str] = "latest",
        **kwargs,
    ):
        """Request generation function. Can be overloaded via inheritance for custom RPC requests.

        Args:
            address (str): address to call
            function_sig (str): function signature
            args (Optional[list], optional): arguments for function if present

        Returns:
            [type]: [description]
        """  # noqa: E501
        data = self.encode_params(function_sig, args, **kwargs)
        return [{"to": address, "data": data}, block_tag]

    def encode_params(  # type: ignore[no-untyped-def]
        self,
        function_sig: str,
        args: Optional[list] = None,  # type: ignore[type-arg]
        arg_types: Optional[list] = None,  # type: ignore[type-arg]
        **kwargs,
    ) -> str:
        """Encode eth_call data by first taking the function sighash, then adding the encoded data

        Args:w
            function_sig (str): function signature
            args (Optional[list], optional): arguments to pass. Defaults to None.

        Returns:
            str: [description]
        """  # noqa: E501
        b = bytes.fromhex(function_signature_to_sighash(function_sig)[2:])

        if args is not None:
            if arg_types is None:
                start = function_sig.find("(")
                arg_types = function_sig[start:].strip("()").split(",")

                if type(arg_types) == str:  # type: ignore[comparison-overlap]
                    arg_types = [arg_types]

            b += encode_abi(arg_types, args)

        return to_hex(b)

    def decode_response(self, response: dict, return_types: list[str]) -> Optional[Any]:  # type: ignore[type-arg]  # noqa: E501
        """Decode responses, filling None for any errored requests

        Args:
            response (dict): [description]
            return_types (list[str]): [description]

        Returns:
            Optional[Any]: [description]
        """
        try:
            data = response.get("result")
            if data is None:
                return None

            trimmed = data[2:]
            if trimmed == "":
                return None

            parsed = decode_abi(return_types, bytes.fromhex(trimmed))
            n_expected, n_received = len(return_types), len(parsed)

            if n_expected == 1 or n_received == 1:
                return parsed[0]
            elif n_expected < n_received:
                return parsed[:n_expected]
            else:
                return parsed

        except Exception:
            return None
