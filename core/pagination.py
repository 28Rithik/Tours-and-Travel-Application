"""
Core Reusable Pagination Engine for TravelERP.

Provides production-ready, memory-efficient pagination for both template-rendered
HTML views and high-throughput REST JSON API endpoints.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger, Page
from django.http import HttpRequest, JsonResponse


class PaginationResult:
    """
    Structured container holding paginated queryset slices and navigation metadata.
    Designed for seamless use in both Django templates and JSON responses.
    """

    def __init__(
        self,
        page_obj: Page,
        paginator: Paginator,
        page_size: int,
        window: int = 2,
    ):
        self.page_obj = page_obj
        self.paginator = paginator
        self.page_size = page_size
        self.total_count = paginator.count
        self.total_pages = paginator.num_pages
        self.current_page = page_obj.number
        self.records = page_obj.object_list
        self.has_next = page_obj.has_next()
        self.has_previous = page_obj.has_previous()
        self.next_page_number = page_obj.next_page_number() if self.has_next else None
        self.previous_page_number = (
            page_obj.previous_page_number() if self.has_previous else None
        )
        self.window = window

    @property
    def page_range(self) -> List[Union[int, str]]:
        """
        Calculates an intelligent, condensed pagination range with ellipsis (...)
        e.g., [1, 2, '...', 7, 8, 9, '...', 25] for clean UI rendering.
        """
        if self.total_pages <= 7:
            return list(range(1, self.total_pages + 1))

        pages: List[Union[int, str]] = []
        left_bound = max(1, self.current_page - self.window)
        right_bound = min(self.total_pages, self.current_page + self.window)

        # Include start
        if left_bound > 1:
            pages.append(1)
            if left_bound > 2:
                pages.append("...")

        # Current page window
        for p in range(left_bound, right_bound + 1):
            pages.append(p)

        # Include end
        if right_bound < self.total_pages:
            if right_bound < self.total_pages - 1:
                pages.append("...")
            pages.append(self.total_pages)

        return pages

    def as_dict(self, serializer_fn: Optional[Callable[[Any], Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Serializes the paginated result into a standard API response dictionary.
        """
        if serializer_fn:
            serialized_records = [serializer_fn(item) for item in self.records]
        elif hasattr(self.records, "values"):
            serialized_records = list(self.records.values())
        else:
            serialized_records = list(self.records)

        return {
            "success": True,
            "pagination": {
                "count": self.total_count,
                "total_pages": self.total_pages,
                "current_page": self.current_page,
                "page_size": self.page_size,
                "has_next": self.has_next,
                "has_previous": self.has_previous,
                "next_page": self.next_page_number,
                "previous_page": self.previous_page_number,
            },
            "results": serialized_records,
        }


def paginate_queryset(
    queryset: Any,
    request: HttpRequest,
    default_page_size: int = 25,
    max_page_size: int = 100,
    page_param: str = "page",
    page_size_param: str = "page_size",
) -> PaginationResult:
    """
    Safely paginates any Django QuerySet or list-like collection based on request GET parameters.

    Features:
    - Protects against malicious page_size parameters (bounded by max_page_size)
    - Gracefully handles non-integer and out-of-bound page indices
    - Guarantees zero unhandled exceptions on invalid user input
    """
    # 1. Determine safe page size
    raw_page_size = request.GET.get(page_size_param)
    try:
        page_size = int(raw_page_size) if raw_page_size else default_page_size
        page_size = max(1, min(page_size, max_page_size))
    except (ValueError, TypeError):
        page_size = default_page_size

    paginator = Paginator(queryset, page_size)

    # 2. Determine safe page number
    raw_page = request.GET.get(page_param, 1)
    try:
        page_number = int(raw_page)
    except (ValueError, TypeError):
        page_number = 1

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        # If user requests page 9999, return last available page; if empty, empty page
        if paginator.num_pages > 0:
            page_obj = paginator.page(paginator.num_pages)
        else:
            page_obj = paginator.page(1)

    return PaginationResult(page_obj=page_obj, paginator=paginator, page_size=page_size)


def paginated_api_response(
    queryset: Any,
    request: HttpRequest,
    serializer_fn: Optional[Callable[[Any], Dict[str, Any]]] = None,
    default_page_size: int = 25,
    max_page_size: int = 100,
    extra_meta: Optional[Dict[str, Any]] = None,
) -> JsonResponse:
    """
    Utility wrapper that paginates a queryset and directly returns a standardized JsonResponse.
    """
    paginated = paginate_queryset(
        queryset=queryset,
        request=request,
        default_page_size=default_page_size,
        max_page_size=max_page_size,
    )
    payload = paginated.as_dict(serializer_fn=serializer_fn)
    if extra_meta:
        payload.update(extra_meta)

    return JsonResponse(payload)
