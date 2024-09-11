import logging

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_204_NO_CONTENT

from .. import crud
from ..config import DEFAULT_PROJECT_ID, DICOMWEB_BASE_URL_WADO_URI
from ..database import get_session

router = APIRouter()


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# WADO-RS routes


@router.get("/wado", tags=["WADO-URI"])
async def retrieve_instance(
    request: Request, session: AsyncSession = Depends(get_session)
):
    """This endpoint is used to retrieve instances from the DICOMWeb server. It filters the instances based on the studies and series mapped to the project.

    Args:
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """
    # Retrieve all studies mapped to the project
    studies = set(
        await crud.get_all_studies_mapped_to_project(session, DEFAULT_PROJECT_ID)
    )

    # check if studyUID is in the query parameters
    if "studyUID" in request.query_params:
        # Check if the requested studies are mapped to the project
        requested_studies = set(request.query_params.getlist("studyUID"))
        studies = studies.intersection(requested_studies)

    query_params = dict(request.query_params)
    query_params["studyUID"] = []

    # Add only the studies mapped to the project to the query parameters
    for study_uid in studies:
        query_params["studyUID"].append(study_uid)

    if "seriesUID" in request.query_params:
        series_in_query_params = set(request.query_params.getlist("seriesUID"))

        all_mapped_series = set(
            await crud.get_series_instance_uids_of_study_which_are_mapped_to_project(
                session=session,
                project_id=DEFAULT_PROJECT_ID,
                study_instance_uid=list(studies)[
                    0
                ],  # If seriesUID is present, providing multiple studies is not supported (Ambiguity)
            )
        )

        series = all_mapped_series.intersection(series_in_query_params)

        query_params["seriesUID"] = []
        for series_uid in series:
            query_params["seriesUID"].append(series_uid)

    # Update the query parameters
    request._query_params = query_params

    async def stream_study():
        """Stream the study instances from the DICOMWeb server.

        Yields:
            bytes: DICOM instance
        """
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{DICOMWEB_BASE_URL_WADO_URI}",
                params=request.query_params,
                headers=dict(request.headers),
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream_study())
