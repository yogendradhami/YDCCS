
from .models import GoogleReview, GoogleBusinessProfileLocation


def _normalize_star_rating(star_rating):
    if isinstance(star_rating, str):
        normalized_rating = star_rating.strip().upper()
        mapping = {
            "ONE": 1,
            "TWO": 2,
            "THREE": 3,
            "FOUR": 4,
            "FIVE": 5,
        }
        if normalized_rating in mapping:
            return mapping[normalized_rating]
        star_rating = normalized_rating

    try:
        return max(1, min(int(star_rating), 5))
    except (TypeError, ValueError):
        return 5


def _format_rating(rating):
    return "⭐" * _normalize_star_rating(rating)


def get_public_google_reviews(limit=None):
    """Return public-friendly Google reviews from the database."""

    reviews = GoogleReview.objects.order_by(
        "-review_date",
        "-created_at",
    )

    if limit:
        reviews = reviews[:limit]

    return [
        {
            "reviewer_name": review.reviewer_name or "Anonymous",
            "comment": review.comment or "",
            "rating": _format_rating(review.rating),
            "suburb": "",
            "review_date": review.review_date or review.created_at,
            "created_at": review.review_date or review.created_at,
            "review_url": review.review_url,
            "reviewer_photo": review.reviewer_photo,
        }
        for review in reviews
    ]


def get_public_google_review_stats():
    """
    Return official Google statistics when available.
    Fall back to locally stored reviews if official statistics are absent.
    """

    location = (
        GoogleBusinessProfileLocation.objects
        .filter(is_selected=True)
        .first()
    )

    if location:
        official_count = location.google_total_review_count
        official_average = location.google_average_rating

        if official_count is not None and official_average is not None:
            return {
                "review_count": official_count,
                "average_rating": round(float(official_average), 1),
                "stats_source": "google",
                "last_synced_at": location.reviews_last_synced_at,
            }

    local_reviews = list(
        GoogleReview.objects.exclude(rating="")
    )

    if not local_reviews:
        return {
            "review_count": 0,
            "average_rating": 0.0,
            "stats_source": "local",
            "last_synced_at": (
                location.reviews_last_synced_at if location else None
            ),
        }

    ratings = [
        _normalize_star_rating(review.rating)
        for review in local_reviews
    ]

    return {
        "review_count": len(local_reviews),
        "average_rating": round(sum(ratings) / len(ratings), 1),
        "stats_source": "local",
        "last_synced_at": (
            location.reviews_last_synced_at if location else None
        ),
    }


def get_google_reviews_api():
    """Fetch live Google reviews from the selected profile location."""

    from .business_profile import GoogleBusinessProfileService

    return [
        {
            "reviewer_name": review.get("reviewer", {}).get(
                "displayName",
                "Anonymous",
            ),
            "comment": review.get("comment", ""),
            "rating": _format_rating(review.get("starRating", 5)),
            "created_at": review.get("createTime", ""),
            "review_date": review.get("createTime", ""),
            "review_url": review.get("reviewUrl", ""),
            "reviewer_photo": review.get("reviewer", {}).get(
                "profilePhotoUrl",
                "",
            ),
        }
        for review in GoogleBusinessProfileService().get_selected_reviews()
    ]
