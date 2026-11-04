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

        total_pages = self.page.paginator.num_pages
        current_page = self.page.number
        first_page = 1 if total_pages > 0 else 1
        last_page = total_pages
        next_page = self.page.next_page_number() if self.page.has_next() else None
        previous_page = self.page.previous_page_number() if self.page.has_previous() else None

        return Response({
            'count': self.page.paginator.count,
            'total_pages': total_pages,
            'current': current_page,
            'first': first_page,
            'last': last_page,
            'next': next_page,
            'previous': previous_page,
            'back': previous_page,
            'off': current_page,
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
