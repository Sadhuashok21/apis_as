from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard DRF PageNumberPagination supporting configurable page_size,
    customizable results key ('mods', 'blueprints', 'planets', or 'results'),
    and accepting both ?page= and legacy ?off= query parameters.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    max_page_size = 100
    results_field = 'results'

    def get_page_number(self, request, paginator):
        page_number = request.query_params.get(self.page_query_param) or request.query_params.get('off')
        return page_number or 1

    def get_paginated_response(self, data):
        field_name = getattr(self, 'results_field', None)
        req = getattr(self, 'request', None)
        if req and req.query_params.get('type') == 'mod':
            field_name = 'mods'
        elif req and req.query_params.get('type') == 'planet':
            field_name = 'planets'

        if not field_name:
            field_name = 'results'

        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            field_name: data,
        })


class BlueprintPagination(StandardResultsSetPagination):
    """
    DRF pagination returning 'blueprints' (or 'mods' if ?type=mod is requested).
    """
    results_field = 'blueprints'


class PlanetPagination(StandardResultsSetPagination):
    """
    DRF pagination returning 'planets' as the data key.
    """
    results_field = 'planets'


class ModsPagination(StandardResultsSetPagination):
    """
    DRF pagination returning 'mods' as the data key.
    """
    results_field = 'mods'
