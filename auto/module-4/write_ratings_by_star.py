import random
from typing import TypedDict


class ReviewSummary(TypedDict):
    total_reviews: int
    target_rating: float
    actual_rating: float
    reviews_5_star: int
    reviews_4_star: int
    reviews_3_star: int


MIN_REVIEWS: int = 30
MAX_REVIEWS: int = 60


# Xác suất chọn rating trung bình cho sản phẩm (phân bổ đa dạng từ 4.60 đến 4.80).
TARGET_RATING_WEIGHTS: dict[float, int] = {
    4.80: 15,
    4.75: 20,
    4.70: 30,
    4.65: 20,
    4.60: 15,
}


# Tỷ lệ số sao tương ứng với từng rating trung bình (tối đa hóa lượng 4 sao ở từng mức điểm).
IDEAL_STAR_RATIOS: dict[float, dict[int, float]] = {
    4.80: {
        3: 0.01,
        4: 0.18,
        5: 0.81,
    },
    4.75: {
        3: 0.01,
        4: 0.23,
        5: 0.76,
    },
    4.70: {
        3: 0.02,
        4: 0.26,
        5: 0.72,
    },
    4.65: {
        3: 0.02,
        4: 0.31,
        5: 0.67,
    },
    4.60: {
        3: 0.02,
        4: 0.36,
        5: 0.62,
    },
}


def generate_review_summary(
    min_reviews: int = MIN_REVIEWS,
    max_reviews: int = MAX_REVIEWS,
    seed: int | None = None,
) -> ReviewSummary:
    """
    Tạo thống kê review cho một sản phẩm.

    Quy tắc:
    - Tổng review từ min_reviews đến max_reviews.
    - Không có review 1 hoặc 2 sao.
    - Rating mục tiêu được chọn theo TARGET_RATING_WEIGHTS.
    - Số lượng review 3, 4 và 5 sao được tính sao cho rating thực tế
      gần rating mục tiêu nhất.
    """

    if min_reviews <= 0:
        raise ValueError("min_reviews phải lớn hơn 0.")

    if max_reviews < min_reviews:
        raise ValueError(
            "max_reviews phải lớn hơn hoặc bằng min_reviews."
        )

    rng = random.Random(seed)

    total_reviews = rng.randint(min_reviews, max_reviews)

    target_rating = rng.choices(
        population=list(TARGET_RATING_WEIGHTS.keys()),
        weights=list(TARGET_RATING_WEIGHTS.values()),
        k=1,
    )[0]

    ideal_ratios = IDEAL_STAR_RATIOS[target_rating]

    best_result: tuple[
        tuple[float, float],
        int,
        int,
        int,
        float,
    ] | None = None

    # Thử tất cả tổ hợp số review 3, 4 và 5 sao.
    # Tổng review tối đa chỉ là 90 nên chi phí tính toán rất nhỏ.
    for reviews_3_star in range(total_reviews + 1):
        for reviews_4_star in range(
            total_reviews - reviews_3_star + 1
        ):
            reviews_5_star = (
                total_reviews
                - reviews_3_star
                - reviews_4_star
            )

            # Đảm bảo 4 sao luôn thấp hơn 5 sao nhưng được tối đa hóa cho từng mốc điểm
            if not (0.15 * reviews_5_star <= reviews_4_star < reviews_5_star):
                continue

            actual_rating = (
                reviews_3_star * 3
                + reviews_4_star * 4
                + reviews_5_star * 5
            ) / total_reviews

            rating_error = abs(actual_rating - target_rating)

            ratio_error = (
                abs(
                    reviews_3_star / total_reviews
                    - ideal_ratios[3]
                )
                + abs(
                    reviews_4_star / total_reviews
                    - ideal_ratios[4]
                )
                + abs(
                    reviews_5_star / total_reviews
                    - ideal_ratios[5]
                )
            )

            # Ưu tiên rating trung bình chính xác trước,
            # sau đó mới ưu tiên tỷ lệ số sao gần tỷ lệ mong muốn.
            score = (rating_error, ratio_error)

            if best_result is None or score < best_result[0]:
                best_result = (
                    score,
                    reviews_3_star,
                    reviews_4_star,
                    reviews_5_star,
                    actual_rating,
                )

    if best_result is None:
        raise RuntimeError("Không thể tạo thống kê review.")

    (
        _,
        reviews_3_star,
        reviews_4_star,
        reviews_5_star,
        actual_rating,
    ) = best_result

    return {
        "total_reviews": total_reviews,
        "target_rating": target_rating,
        "actual_rating": round(actual_rating, 2),
        "reviews_5_star": reviews_5_star,
        "reviews_4_star": reviews_4_star,
        "reviews_3_star": reviews_3_star,
    }


def write_review_summary_to_file(
    summary: ReviewSummary,
    file_path: str = "reviews-rule.txt",
) -> None:
    """
    Viết kết quả thống kê review vào file văn bản (ghi đè file).
    """
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Tổng số review: {summary['total_reviews']}\n")
        f.write(f"Rating mục tiêu: {summary['target_rating']}\n")
        f.write(f"Rating thực tế: {summary['actual_rating']}\n")
        f.write(f"Review 5 sao: {summary['reviews_5_star']}\n")
        f.write(f"Review 4 sao: {summary['reviews_4_star']}\n")
        f.write(f"Review 3 sao: {summary['reviews_3_star']}\n")


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    result = generate_review_summary()

    print(f"Tổng số review: {result['total_reviews']}")
    print(f"Rating mục tiêu: {result['target_rating']}")
    print(f"Rating thực tế: {result['actual_rating']}")
    print(f"Review 5 sao: {result['reviews_5_star']}")
    print(f"Review 4 sao: {result['reviews_4_star']}")
    print(f"Review 3 sao: {result['reviews_3_star']}")

    write_review_summary_to_file(result, "reviews-rule.txt")
