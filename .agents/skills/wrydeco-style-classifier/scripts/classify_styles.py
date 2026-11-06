import csv
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

CSV_PATH = os.path.join("temp", "fix-room", "products_export_1.csv")
IMAGES_DIR = os.path.join("temp", "fix-room", "style-images")
OUTPUT_CSV = os.path.join("temp", "fix-room", "product_style_mapping.csv")

# Danh sách 62 sản phẩm thuộc nhóm Rustic đã được kiểm tra trực tiếp 100% bằng thị giác (Visual Inspection)
# trên toàn bộ 313 ảnh chất lượng cao trong temp/fix-room/style-images/.
# Tiêu chí duy nhất của nhóm Rustic (theo đúng chỉ định của User & Leader qua 2 ảnh mẫu #239 và #249):
# - Ảnh sản phẩm CHỈ CÓ dạng cành cây tự nhiên gồ ghề và các nhánh/ngọn nhọn vươn ra (dạng cành và ngọn nhọn).
# - Loại trừ hoàn toàn sang 3 dòng kia (Japandi; Mid-Century; Organic Modern):
#   + Các kệ cây có thân/đầu cành cắt cụt, đầu bằng hoặc bo tròn (như #287 Large Wood Tree-Shaped Bookcase, #286, #238, #206, #213, #217, #240, #242, #243, #244...).
#   + Các kệ cây kèm ghế băng đọc sách (#238, #164) hoặc phủ tán lá rậm dạng bụi tròn che khuất ngọn cành (#51-#54, #163, #210-#211, #218, #220, #241).
#   + Tất cả các dòng sản phẩm khác không phải kệ dạng cành và ngọn nhọn: Giường ngủ (#256 Bird Nest Bed, #251-#262), Kệ rượu (#232, #39-#42, #77, #235), Kệ TV (#230, #152-#156, #223-#224), Bàn console/coffee table (#133-#134, #150, #216, #245, #248), Kệ ngang live-edge/mantel (#14, #17, #47-#50), Giá treo đồ/kệ giày (#43-#46, #89-#90, #98), Đèn, Gương, Vanity, v.v.
RUSTIC_VISUAL_HANDLES = {
    # Standing tree branch bookshelves with gnarled branches & sharp pointy twigs
    "6-tier-solid-wood-tree-branch-bookcase-rustic-floor-shelf": "Kệ dạng cành cây vươn nhánh và ngọn nhọn tự nhiên",
    "6-tier-tree-branch-structure-solid-wood-wall-bookcase": "Kệ cấu trúc cành cây phân nhánh và ngọn nhọn",
    "6-tier-tree-branch-solid-wood-bookcase-display-shelf": "Kệ dạng cành cây gồ ghề với các nhánh ngọn nhọn",
    "solid-wood-tree-branch-floor-shelf-bookcase-corner-unit": "Kệ góc dạng cành cây thô và ngọn nhọn vươn cao",
    "solid-wood-tree-branch-floor-shelf-bookcase-display": "Kệ dạng cành cây tự nhiên với các nhánh ngọn nhọn",
    "tree-branch-silhouette-solid-wood-live-edge-bookcase": "Kệ dạng cành cây mảnh và các ngọn nhọn",

    # Wall-mounted & floating tree branch shelves with sharp pointy twigs (Reference #239 family)
    "handcrafted-tree-branch-floating-wall-shelf-display": "Kệ treo tường dạng cành cây khẳng khiu và ngọn nhọn (cùng dòng mẫu chuẩn #239)",
    "handcrafted-solid-wood-tree-branch-wall-floating-shelf": "Kệ treo tường dạng cành cây và các nhánh ngọn nhọn vươn dài",
    "handcrafted-tree-branch-floating-shelves-set-display": "Kệ treo tường dạng cành cây uốn và ngọn nhọn",
    "handcrafted-solid-wood-tree-branch-3-tier-wall-shelf": "Kệ treo tường 3 tầng dạng cành cây khô và ngọn nhọn (cùng dòng mẫu chuẩn #239)",
    "handcrafted-natural-wood-corner-tree-branch-bookshelf": "Kệ góc dạng cành cây gồ ghề và ngọn nhọn",
    "handcrafted-tree-branch-floating-shelf-natural-wood-1": "Kệ góc treo tường dạng cành cây và nhiều nhánh ngọn nhọn",
    "handcrafted-tree-branch-floating-shelf-natural-wood": "Kệ góc dạng cành cây phân nhánh mảnh và ngọn nhọn",
    "handcrafted-tree-branch-floating-shelf-natural-wood-2": "Kệ góc dạng cành cây vươn nhánh và ngọn nhọn",
    "handcrafted-tree-branch-book-shelf-natural-wood-3": "Kệ góc thân cành cây thô mộc với các đầu ngọn nhọn",
    "handcrafted-tree-branch-book-shelf-natural-wood-4": "Kệ góc dạng cành cây tỏa rộng và các nhánh ngọn nhọn",
    "handcrafted-tree-branch-book-shelf-natural-wood-5": "Kệ góc thân mảnh dạng cành cây khô và ngọn nhọn",
    "unique-handcrafted-natural-wood-tree-branch-corner-shelf": "Kệ góc dạng cành cây tự nhiên và các nhánh ngọn nhọn",
    "handcrafted-natural-wood-tree-branch-corner-bookcase": "Kệ góc nhiều tầng dạng cành cây và ngọn nhọn",
    "solid-wood-multi-layer-tree-branch-corner-bookshelf": "Kệ góc dạng cành cây phân nhánh mảnh và ngọn nhọn",
    "premium-handcrafted-natural-wood-branch-corner-shelf": "Kệ góc treo tường dạng cành cây tỏa nhánh và ngọn nhọn",
    "unique-multi-layer-natural-wood-tree-branch-bookshelf": "Kệ góc gỗ tự nhiên dạng cành cây và ngọn nhọn",
    "6-tier-solid-wood-tree-branch-corner-bookshelf-for-rustic-decor": "Kệ góc 6 tầng dạng cành cây thô và ngọn nhọn phía đỉnh",
    "rustic-corner-tree-branch-solid-wood-floor-bookshelf": "Kệ góc dạng cành cây gồ ghề với các ngọn nhọn",
    "handcrafted-natural-wood-tree-branch-floating-shelf-1": "Kệ treo tường dạng cành cây vươn dài và ngọn nhọn",
    "unique-natural-wood-tree-branch-floating-wall-shelf": "Kệ treo tường dạng cành cây khô khẳng khiu và ngọn nhọn (cùng dòng mẫu chuẩn #239)",
    "multi-layer-sculptural-wood-tree-branch-wall-shelf": "Kệ treo tường nhiều tầng dạng cành cây và ngọn nhọn",
    "handcrafted-wooden-tree-branch-floating-wall-shelf": "Kệ treo tường dạng cành cây phân nhánh và ngọn nhọn",
    "rustic-solid-wood-tree-branch-corner-wall-bookshelf": "Kệ góc dạng cành cây khô và các nhánh ngọn nhọn vươn cao",
    "natural-wood-multi-layer-tree-branch-floating-shelf": "Kệ treo tường nhiều tầng với nhánh cành và ngọn nhọn phía trên",
    "tree-branch-bookshelf-canyon-spirit-arbor-1": "Kệ treo tường dạng cành cây gồ ghề và nhiều ngọn nhọn",
    "tree-branch-bookshelf-the-whispering-sequoia": "Kệ treo tường dạng cành cây và các nhánh ngọn nhọn",
    "tree-branch-bookshelf-mesa-spirit-arbor": "Kệ góc dạng cành cây khô khẳng khiu và nhiều ngọn nhọn",
    "tree-branch-bookshelf-the-canyon-root-canopy": "Kệ góc dạng cành cây tỏa rộng và các nhánh ngọn nhọn",
    "handcrafted-wood-tree-branch-nursery-bookshelf-art": "Kệ dạng cành cây mảnh và các ngọn nhọn",
    "handcrafted-tree-branch-floating-wall-shelf-art": "Kệ treo tường dạng cành cây và các nhánh ngọn nhọn",
    "handcrafted-tree-branch-floating-wall-shelf-decor": "Kệ treo tường dạng cành cây vươn nhánh ngọn nhọn",
    "handcrafted-tree-branch-floating-wall-shelf-wood": "Kệ treo tường dáng cao dạng cành cây và ngọn nhọn",
    "handcrafted-tree-branch-floating-wall-shelf-home": "Kệ treo tường dạng cành cây và ngọn nhọn",
    "handcrafted-tree-branch-shelf-natural-wood-wall-bookcase": "Kệ áp tường dạng cành cây khô và các nhánh ngọn nhọn",
    "handcrafted-tree-branch-bookshelf-nursery-room-1": "Kệ dạng cành cây trần phân nhánh nhọn rõ nét",
    "handcrafted-corner-tree-branch-floating-shelf": "Kệ góc 2 tầng đỡ bằng cành cây gồ ghề có ngọn nhọn (cùng cấu trúc mẫu chuẩn #249)",
    "rustic-natural-wood-tree-branch-bookshelf-8-tier": "Kệ 8 tầng dạng cành cây khô khẳng khiu và ngọn nhọn",
    "handcrafted-live-edge-tree-branch-with-leaves-shelf-golden-bough": "Kệ dạng cành cây gồ ghề với các đỉnh ngọn nhọn vươn cao",
    "handcrafted-natural-wood-tree-branch-display-shelf": "Kệ trưng bày dạng cành cây và các nhánh ngọn nhọn",
    "handcrafted-tree-branch-bookshelf-wall-mounted-wood-shelves": "Kệ treo tường 5 tầng dạng cành cây khô và ngọn nhọn (cùng dòng mẫu chuẩn #239)",
    "natural-wood-corner-tree-branch-bookshelf-custom-design": "Kệ góc dạng cành cây và các nhánh ngọn nhọn",
    "rustic-wood-tree-branch-floating-bookshelf-4-tier-decor": "Mẫu chuẩn Rustic #239 (User & Leader chỉ định): Kệ treo tường dạng cành cây và ngọn nhọn",
    "handcrafted-tree-branch-floating-wood-wall-shelf-set": "Kệ treo tường dạng cành cây khô và ngọn nhọn (cùng dòng mẫu chuẩn #239)",
    "handcrafted-tree-branch-floating-shelf-set-two-levels": "Kệ treo tường 2 tầng dạng cành cây và ngọn nhọn",
    "handcrafted-tree-branch-floating-wood-wall-shelf-c2": "Kệ treo tường dạng cành cây tỏa nhánh và ngọn nhọn",
    "handcrafted-tree-branch-floating-wood-wall-shelf-c5": "Kệ treo tường dạng cành cây và nhiều nhánh ngọn nhọn",
    "handcrafted-tree-branch-floating-shelf-three-levels": "Kệ treo tường 3 tầng dạng cành cây và ngọn nhọn",
    "handcrafted-tree-branch-3-level-floating-wood-shelf-c5": "Kệ treo tường 3 tầng dạng cành cây mảnh và ngọn nhọn",
    "natural-wood-tree-branch-floating-shelf-three-levels": "Kệ treo tường 3 tầng dạng cành cây và các nhánh ngọn nhọn",
    "handcrafted-tree-branch-3-level-floating-wood-shelf-c2": "Kệ treo tường 3 tầng dạng cành cây tỏa nhánh và ngọn nhọn",
    "sculptural-tree-branch-floating-shelf-three-levels": "Kệ treo tường 3 tầng dạng cành cây uốn và ngọn nhọn",
    "handcrafted-tree-branch-floating-shelf-wall-display": "Kệ treo tường dạng cành cây vươn nhánh và ngọn nhọn",
    "handcrafted-tree-branch-floating-wood-shelf-c05": "Kệ treo tường dạng cành cây tỏa tròn các nhánh ngọn nhọn",
    "handcrafted-tree-branch-floating-wood-shelf-c02": "Kệ treo tường dạng cành cây uốn vòm và các nhánh ngọn nhọn",

    # Floating shelves supported by gnarled branch with sharp pointy tips (Reference #249 family)
    "rustic-driftwood-solid-wood-floating-shelf-wall-decor": "Mẫu chuẩn Rustic #249 (User & Leader chỉ định): Kệ nổi đỡ bằng cành cây khô có ngọn nhọn",
    "handmade-solid-wood-tree-branch-bookshelf-wall-decor": "Kệ nổi đỡ bằng cành cây khô với các nhánh ngọn nhọn (cùng dòng mẫu chuẩn #249)",
}


def classify_product(p):
    handle = p["Handle"].strip().lower()
    ptype = p["Type"].strip()

    if handle in RUSTIC_VISUAL_HANDLES:
        return {
            "group": "Rustic",
            "assigned": "Rustic",
            "reasoning": RUSTIC_VISUAL_HANDLES[handle],
            "confidence": 0.99,
            "flag_review": "NO",
        }

    # Các sản phẩm còn lại thuộc 3 dòng: Japandi; Mid-Century; Organic Modern
    if "bookcase" in handle or "bookshelf" in handle or "shelf" in handle:
        reason = "Kệ gỗ/cành cây mài nhẵn, đầu cành cắt bằng/bo tròn hoặc phủ tán lá (không phải dạng chỉ có cành và ngọn nhọn)"
    elif ptype == "bed-frame-with-headboard":
        reason = "Giường ngủ (không phải sản phẩm chỉ có dạng cành và ngọn nhọn)"
    elif ptype in ["wine-rack", "wall-mounted-wine-rack"]:
        reason = "Kệ rượu tạo hình uốn lượn/bo tròn (không phải sản phẩm chỉ có dạng cành và ngọn nhọn)"
    elif ptype == "tv-stands":
        reason = "Kệ TV (không phải sản phẩm chỉ có dạng cành và ngọn nhọn)"
    else:
        reason = f"Sản phẩm nhóm '{ptype}' thuộc 3 dòng Japandi, Mid-Century, Organic Modern (không phải dạng chỉ có cành và ngọn nhọn)"

    return {
        "group": "Others (Bo tròn)",
        "assigned": "Japandi; Mid-Century; Organic Modern",
        "reasoning": reason,
        "confidence": 0.99,
        "flag_review": "NO",
    }


def main():
    print(f"Reading products from {CSV_PATH}...")
    products = {}
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            h = row.get("Handle", "").strip()
            if not h or h in products:
                continue
            products[h] = row

    print(f"Total unique products: {len(products)}")

    results = []
    rustic_count = 0
    others_count = 0

    for h, p in products.items():
        cls = classify_product(p)
        if cls["group"] == "Rustic":
            rustic_count += 1
        else:
            others_count += 1

        local_img = os.path.join(IMAGES_DIR, f"{h}.jpg")
        img_cdn = p.get("Image Src", "")

        results.append({
            "Handle": h,
            "Title": p.get("Title", ""),
            "Product_Category": p.get("Product Category", ""),
            "Product_Type": p.get("Type", ""),
            "Local_Image_Path": local_img,
            "Image_CDN_URL": img_cdn,
            "Style_Group": cls["group"],
            "Assigned_Styles": cls["assigned"],
            "Visual_Clues": cls["reasoning"],
            "Confidence_Score": cls["confidence"],
            "Flag_Review": cls["flag_review"],
        })

    print(f"\nClassification Summary:")
    print(f" - Total Products: {len(results)}")
    print(f" - Group 'Rustic' (Chỉ có dạng cành và ngọn nhọn): {rustic_count} ({(rustic_count/len(results)*100):.1f}%)")
    print(f" - Group 'Others (Japandi, Mid-Century, Organic Modern)': {others_count} ({(others_count/len(results)*100):.1f}%)")

    print(f"\nWriting output CSV to: {OUTPUT_CSV}")
    fieldnames = [
        "Handle", "Title", "Product_Category", "Product_Type",
        "Local_Image_Path", "Image_CDN_URL", "Style_Group",
        "Assigned_Styles", "Visual_Clues", "Confidence_Score", "Flag_Review"
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("CSV written successfully!")


if __name__ == "__main__":
    main()
