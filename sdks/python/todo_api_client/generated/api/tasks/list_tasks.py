from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx2

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.status_filter import StatusFilter
from ...models.task_output import TaskOutput
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    status: None | StatusFilter | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_status: None | str | Unset
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, StatusFilter):
        json_status = status.value
    else:
        json_status = status
    params["status"] = json_status

    json_limit: int | None | Unset
    if isinstance(limit, Unset):
        json_limit = UNSET
    else:
        json_limit = limit
    params["limit"] = json_limit

    params["offset"] = offset


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/tasks",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx2.Response) -> ErrorResponse | HTTPValidationError | list[TaskOutput] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = TaskOutput.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if response.status_code == 429:
        response_429 = ErrorResponse.from_dict(response.json())



        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx2.Response) -> Response[ErrorResponse | HTTPValidationError | list[TaskOutput]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    status: None | StatusFilter | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> Response[ErrorResponse | HTTPValidationError | list[TaskOutput]]:
    """ Lista tarefas

     Retorna as tarefas na ordem de criação, opcionalmente paginadas.

    Args:
        status (None | StatusFilter | Unset): Filtra por status; omitido = todas.
        limit (int | None | Unset): Máximo de tarefas na página; omitido = todas.
        offset (int | Unset): Quantas tarefas pular (depois do filtro). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | list[TaskOutput]]
     """


    kwargs = _get_kwargs(
        status=status,
limit=limit,
offset=offset,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    status: None | StatusFilter | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> ErrorResponse | HTTPValidationError | list[TaskOutput] | None:
    """ Lista tarefas

     Retorna as tarefas na ordem de criação, opcionalmente paginadas.

    Args:
        status (None | StatusFilter | Unset): Filtra por status; omitido = todas.
        limit (int | None | Unset): Máximo de tarefas na página; omitido = todas.
        offset (int | Unset): Quantas tarefas pular (depois do filtro). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | list[TaskOutput]
     """


    return sync_detailed(
        client=client,
status=status,
limit=limit,
offset=offset,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    status: None | StatusFilter | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> Response[ErrorResponse | HTTPValidationError | list[TaskOutput]]:
    """ Lista tarefas

     Retorna as tarefas na ordem de criação, opcionalmente paginadas.

    Args:
        status (None | StatusFilter | Unset): Filtra por status; omitido = todas.
        limit (int | None | Unset): Máximo de tarefas na página; omitido = todas.
        offset (int | Unset): Quantas tarefas pular (depois do filtro). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | list[TaskOutput]]
     """


    kwargs = _get_kwargs(
        status=status,
limit=limit,
offset=offset,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    status: None | StatusFilter | Unset = UNSET,
    limit: int | None | Unset = UNSET,
    offset: int | Unset = 0,

) -> ErrorResponse | HTTPValidationError | list[TaskOutput] | None:
    """ Lista tarefas

     Retorna as tarefas na ordem de criação, opcionalmente paginadas.

    Args:
        status (None | StatusFilter | Unset): Filtra por status; omitido = todas.
        limit (int | None | Unset): Máximo de tarefas na página; omitido = todas.
        offset (int | Unset): Quantas tarefas pular (depois do filtro). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | list[TaskOutput]
     """


    return (await asyncio_detailed(
        client=client,
status=status,
limit=limit,
offset=offset,

    )).parsed
