import os
import csv
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

HUE_HOTELS_URL = "https://www.tripadvisor.com/Hotels-g2146376-Thua_Thien_Hue_Province-Hotels.html"
PROVINCE = "Thua Thien Hue"

def extract_number_of_reviews(text):
    if not text: return "0"
    m = re.search(r'([\d,]+)\s*reviews?', text, re.IGNORECASE)
    if m:
        return m.group(1).replace(',', '')
    return "0"

def scrape():
    print("================== TRÌNH CÀO DỮ LIỆU TRIPADVISOR ==================")
    print("Khởi động tính năng Lưu Nối Tiếp. Đang đọc lại dữ liệu cũ nếu có...")
    
    # 1. Nạp danh sách khách sạn đã cào
    existing_hotels = set()
    hotel_list = []
    if os.path.exists('hotels_hue_summary.csv'):
        with open('hotels_hue_summary.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_hotels.add(row['hotel_url'])
                hotel_list.append(row)
        print(f"-> Đã tìm thấy {len(hotel_list)} khách sạn từ file cũ.")

    # 2. Nạp danh sách review đã cào (Duyệt theo ID: URL + Comment)
    existing_reviews = set()
    if os.path.exists('hotels_hue_reviews_jan2025.csv'):
        with open('hotels_hue_reviews_jan2025.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_reviews.add((row['url'], row['comment']))
        print(f"-> Đã tìm thấy {len(existing_reviews)} reviews từ file cũ.")

    with Stealth().use_sync(sync_playwright()) as p:
        # Bật headless=False để hiển thị trình duyệt cho bạn xem và giải Captcha nếu cần
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        # Áo tàng hình đã được tự động khoác lên nhờ Stealth().use_sync() ở trên
        
        # BƯỚC 1: Cào danh sách khách sạn nếu chưa lấy đủ (để cào tất cả mọi khách sạn, có thể nới lỏng con số này)
        if True: # Luôn quét danh sách KS để tìm KS mới, có thể sửa về 'if len(hotel_list) == 0:' nếu không muốn quét lại
            print("\n=== BƯỚC 1: LẤY DANH SÁCH KHÁCH SẠN ===")
            print("Đang truy cập danh sách khách sạn tại Thừa Thiên Huế...")
            try:
                page.goto(HUE_HOTELS_URL, timeout=60000)
                page.wait_for_timeout(5000)
                
                # Trang chủ khách sạn giờ bị gom gọn chỉ còn cỡ 25 khách sạn nổi bật.
                # Bắt buộc phải click nút "See all 1000+ hotels" để mở rộng trang và gọi ra nút Next.
                try:
                    btns = page.locator('button:has-text("See all"), a:has-text("See all")').all()
                    for btn in btns:
                        txt = btn.inner_text().lower()
                        if "hotels" in txt or "properties" in txt or "see all" in txt:
                            btn.click(timeout=3000)
                            page.wait_for_timeout(4000)
                            print("  => (Đã kích hoạt chế độ hiển thị toàn bộ bộ sưu tập khách sạn)")
                            break
                except Exception:
                    pass
                    
            except Exception as e:
                print(f"Lỗi khi tải trang ban đầu: {e}")
                
            page_num = 1
            
            # Ghi nối tiếp 'a'
            file_exists = os.path.exists('hotels_hue_summary.csv')
            with open('hotels_hue_summary.csv', 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['hotel_url', 'hotel_name', 'number_of_reviews'])
                if not file_exists:
                    writer.writeheader()
                # Sử dụng vòng lặp vô hạn để lấy toàn bộ các trang khách sạn
                while True:
                    print(f"Đang duyệt trang danh sách thứ {page_num}...")
                    for _ in range(5):
                        page.mouse.wheel(0, 1000)
                        page.wait_for_timeout(1000)
                    
                    # Sử dụng selector chung rộng lượng nhất, sau đó sẽ lọc lại
                    elements = page.locator('a[href*="/Hotel_Review-"]').all()
                    seen_this_page = set()
                    for el in elements:
                        try:
                            title = el.inner_text().strip()
                            href = el.get_attribute('href')
                            
                            if href and href not in seen_this_page and title and len(title) > 2:
                                # TUYỆT ĐỐI KHÔNG LẤY CÁC KHÁCH SẠN QUẢNG CÁO NẰM NGOÀI HUẾ (NEW YORK, PARIS, V.V..)
                                if "Thua_Thien_Hue_Province" not in href:
                                    continue
                                    
                                seen_this_page.add(href)
                                title = re.sub(r'^\d+\.\s*', '', title)
                                hotel_url = href if href.startswith("http") else "https://www.tripadvisor.com" + href
                                
                                # Lọc bỏ rác và tab REVIEWS để lấy đúng link KS gốc
                                if "#REVIEWS" in hotel_url:
                                    continue
                                    
                                hotel_data = {
                                    'hotel_url': hotel_url,
                                    'hotel_name': title,
                                    'number_of_reviews': 'Xem khi lặp Review'
                                }
                                
                                # Nếu khách sạn chưa từng có trong file, ta ghi mới!
                                if hotel_url not in existing_hotels:
                                    existing_hotels.add(hotel_url)
                                    hotel_list.append(hotel_data)
                                    writer.writerow(hotel_data)
                                    f.flush() # Lưu chặt tay ngay lập tức
                                    print(f"  + Lấy GIỮ MỚI: {title}")
                        except Exception:
                            pass
                            
                    next_btn = page.locator('a.nav.next.primary, a[aria-label="Next page"]')
                    if next_btn.count() > 0 and next_btn.is_visible():
                        try:
                            next_btn.click()
                            page.wait_for_timeout(4000)
                            page_num += 1
                        except Exception:
                            break
                    else:
                        print("Đã hết trang danh sách khách sạn.")
                        break
        else:
            print("\n=== BƯỚC 1: HOÀN TẤT KIỂM TRA QUÉT DANH SÁCH ===")
        
        print(f"\n=== ĐÃ TÍCH LŨY TỔNG CỘNG {len(hotel_list)} KHÁCH SẠN ===")
        print("\n=== BƯỚC 2: CÀO REVIEWS TỪ T1/2025 ===")
        
        rev_file_exists = os.path.exists('hotels_hue_reviews_jan2025.csv')
        with open('hotels_hue_reviews_jan2025.csv', 'a', encoding='utf-8', newline='') as f2:
            fieldnames = ['url', 'reviewer_url', 'title', 'comment', 'star', 'trip_type', 'visit_date', 'language', 'province']
            writer2 = csv.DictWriter(f2, fieldnames=fieldnames)
            if not rev_file_exists:
                writer2.writeheader()
                
            for idx, hotel in enumerate(hotel_list):
                print(f"\n[{idx+1}/{len(hotel_list)}] Vào phân tích: {hotel['hotel_name']}")
                
                try:
                    page.goto(hotel['hotel_url'], timeout=60000)
                    page.wait_for_timeout(3000)
                    
                    # Cố gắng chuyển sang chế độ lấy mọi ngôn ngữ
                    lang_all_radio = page.locator('label[for*="language_filterLang_ALL"], input[value="ALL"][name="language"]')
                    if lang_all_radio.count() > 0:
                        try:
                            lang_all_radio.first.click(timeout=3000)
                            page.wait_for_timeout(2000)
                            print("  (Đã chuyển sang chế độ lấy mọi ngôn ngữ)")
                        except Exception:
                            pass
                    
                    review_page = 1
                    should_stop = False
                    total_reviews_saved_for_hotel = 0
                    # Sử dụng vòng lặp vô hạn để lấy TOÀN BỘ review (hoặc đến khi tới đụng ngưỡng thời gian quy định)
                    while True:  
                        page.wait_for_timeout(2000)
                        review_cards = page.locator('div[data-test-target="HR_CC_CARD"]').all()
                        if not review_cards:
                            review_cards = page.locator('div[data-reviewid], .review-container').all()
                            
                        if not review_cards:
                            print("  Hết reviews trên trang này.")
                            break
                            
                        # Đếm để kiểm tra xem trên 1 page toàn các bài cũ hay trùng không
                        reviews_on_page = 0
                        skipped_reviews = 0
                        
                        for card in review_cards:
                            try:
                                data = card.evaluate('''node => {
                                    let title = "";
                                    let comment = "";
                                    let titleEl = node.querySelector('div[data-test-target="review-title"]');
                                    if (titleEl) {
                                        title = titleEl.innerText.trim();
                                        if (titleEl.nextElementSibling) {
                                            comment = titleEl.nextElementSibling.innerText.replace(/Read more$/, '').trim();
                                        }
                                    }
                                    
                                    let visit_date = "";
                                    let trip_type = "";
                                    let spans = Array.from(node.querySelectorAll('span'));
                                    let dateSpan = spans.find(s => s.innerText.trim() === 'Date of stay:');
                                    if (dateSpan && dateSpan.parentElement && dateSpan.parentElement.parentElement) {
                                        visit_date = dateSpan.parentElement.parentElement.innerText.replace('Date of stay:', '').trim();
                                    }
                                    let typeSpan = spans.find(s => s.innerText.trim() === 'Trip type:');
                                    if (typeSpan && typeSpan.parentElement && typeSpan.parentElement.parentElement) {
                                        trip_type = typeSpan.parentElement.parentElement.innerText.replace(/Trip type:\\s*/, '').trim();
                                    }
                                    
                                    let star = 0;
                                    let svg = node.querySelector('svg[data-automation="bubbleRatingImage"] title');
                                    if (svg) {
                                        let m = (svg.textContent || "").match(/([1-5])/);
                                        if (m) star = parseInt(m[1]);
                                    } else {
                                        let svg2 = node.querySelector('svg[aria-label*="bubbles"]');
                                        if (svg2) {
                                            let m = (svg2.getAttribute("aria-label") || svg2.getAttribute("class") || "").match(/([1-5])/);
                                            if (m) star = parseInt(m[1]);
                                        }
                                    }
                                    
                                    let reviewer_url = "";
                                    let aProfile = node.querySelector('a[href*="/Profile/"]');
                                    if (aProfile) {
                                        reviewer_url = "https://www.tripadvisor.com" + aProfile.getAttribute("href");
                                    }
                                    
                                    return {
                                        title: title,
                                        comment: comment,
                                        visit_date: visit_date,
                                        trip_type: trip_type,
                                        star: star,
                                        reviewer_url: reviewer_url
                                    };
                                }''')
                                
                                title = data.get('title', '')
                                comment = data.get('comment', '')
                                visit_date = data.get('visit_date', '')
                                trip_type = data.get('trip_type', '')
                                star = data.get('star', 0)
                                reviewer_url = data.get('reviewer_url', '')
                                    
                                is_old = False
                                if visit_date:
                                    try:
                                        dt = datetime.strptime(visit_date, "%B %Y")
                                        visit_date = f"{dt.month}/{dt.year}"
                                        if dt.year < 2025:
                                            should_stop = True
                                            is_old = True
                                    except:
                                        if "2024" in visit_date or "2023" in visit_date or "2022" in visit_date:
                                            should_stop = True
                                            is_old = True
                                
                                if is_old: continue
                                
                                # Kiểm tra xem liệu cái đánh giá này có trùng file csv không, nếu có: Bỏ Qua
                                tupple_id = (hotel['hotel_url'], comment)
                                if tupple_id in existing_reviews:
                                    skipped_reviews += 1
                                    continue
                                
                                if comment:
                                    writer2.writerow({
                                        'url': hotel['hotel_url'],
                                        'reviewer_url': reviewer_url,
                                        'title': title,
                                        'comment': comment,
                                        'star': star,
                                        'trip_type': trip_type,
                                        'visit_date': visit_date,
                                        'language': 'all',
                                        'province': PROVINCE
                                    })
                                    f2.flush() # Ép lưu vào ổ cứng
                                    existing_reviews.add(tupple_id)
                                    reviews_on_page += 1
                                    total_reviews_saved_for_hotel += 1
                                    print(f"     + [Xong bài thứ {total_reviews_saved_for_hotel}] => {title[:35]}...")
                                    
                            except Exception as e:
                                print(f"     [CẢNH BÁO] Bỏ qua 1 bài đánh giá do khác biệt cấu trúc HTML (Lỗi: {e})")
                        
                        if should_stop:
                            print(f"  ====> KẾT QUẢ: Chạm mốc tháng 1/2025. Tổng cộng cào được {total_reviews_saved_for_hotel} bài của khách sạn này.")
                            break
                        
                        if reviews_on_page == 0 and skipped_reviews > 0:
                            print(f"  ====> BÁO CÁO: Toàn bộ trang {review_page} đều là review trùng cũ. Máy tiệp tục lật trang...")
                        
                        next_rv_btn = page.locator('a.ui_button.nav.next.primary, a[aria-label="Next page"]')
                        if next_rv_btn.count() > 0 and next_rv_btn.is_visible():
                            next_rv_btn.click()
                            review_page += 1
                        else:
                            print(f"  ====> KẾT QUẢ: Hết toàn bộ đánh giá. Tổng cộng cào được {total_reviews_saved_for_hotel} bài của khách sạn này.")
                            break
                            
                except Exception as e:
                    print(f"Lỗi truy cập khách sạn {hotel['hotel_name']}: {e}")

        print("\nHOÀN THÀNH. Đã kết thúc việc cào dữ liệu và lưu nối tiếp 2 file CSV một cách an toàn.")
        browser.close()

if __name__ == '__main__':
    scrape()
