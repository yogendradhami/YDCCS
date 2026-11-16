from .models import GoogleReview


def _normalize_star_rating(star_rating):
    if isinstance(star_rating, str):
        star_rating = star_rating.upper()
        mapping = {
            "ONE": 1,
            "TWO": 2,
            "THREE": 3,
            "FOUR": 4,
            "FIVE": 5,
        }
        return mapping.get(star_rating, 5)

    try:
        return max(1, min(int(star_rating), 5))
    except (TypeError, ValueError):
        return 5


def _format_rating(rating):
    if rating is None:
        return "⭐⭐⭐⭐⭐"

    if isinstance(rating, str):
        try:
            numeric_value = int(rating)
        except ValueError:
            return "⭐⭐⭐⭐⭐"
        return "⭐" * max(1, min(5, numeric_value))

    try:
        numeric_value = int(rating)
    except (TypeError, ValueError):
        return "⭐⭐⭐⭐⭐"

    return "⭐" * max(1, min(5, numeric_value))


def get_public_google_reviews(limit=None):
    """Return public-friendly Google reviews from the database."""

    reviews = GoogleReview.objects.order_by(
        "-review_date",
        "-created_at"
    )

    if limit:
        reviews = reviews[:limit]

    return [
        {
            "reviewer_name": review.reviewer_name or "Anonymous",
            "comment": review.comment or "",
            "rating": _format_rating(review.rating),
            "suburb": "",
            "created_at": review.review_date or review.created_at,
            "review_url": review.review_url,
            "reviewer_photo": review.reviewer_photo,
        }
        for review in reviews
    ]


def get_google_reviews_api():
    """Fetch live Google reviews from the explicitly selected profile location."""
    from .business_profile import GoogleBusinessProfileService

    return [
        {
            "reviewer_name": review.get("reviewer", {}).get(
                "displayName",
                "Anonymous",
            ),
            "comment": review.get("comment", ""),
            "rating": "⭐" * _normalize_star_rating(review.get("starRating", 5)),
            "created_at": review.get("createTime", ""),
            "review_url": review.get("reviewUrl", ""),
            "reviewer_photo": review.get("reviewer", {}).get(
                "profilePhotoUrl",
                "",
            ),
        }
        for review in GoogleBusinessProfileService().get_selected_reviews()
    ]
