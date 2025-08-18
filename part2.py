            print("No previous scanned URLs file found. Starting fresh.") 

        # Clear the file at start
        with open(scanned_urls_file, 'w') as f: 
            pass 

        suitable_listings.clear() 
        current_listing_index = 0 

        while True:
            # Clear temporary variables at start of each loop.
            if 'current_listing_images' in globals():
                for img in current_listing_images:
                    try:
                        img.close()  # Close all images
                    except Exception as e:
                        print(f"Error closing image: {str(e)}")
                current_listing_images.clear()  # Clear the list
            listings_scanned = 0
            scanned_urls = []
            scanned_urls.clear()
            current_listing_index = 0
            listing_queue.clear()
            listing_queue = []
            
            # Get fresh marketplace page
            driver.get(marketplace_url) 
            print(f"Searching for: {search_query}") 
            main_window = driver.current_window_handle 

            try:
                # Wait for marketplace to load
                WebDriverWait(driver, 30).until( 
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']")) 
                ) 
                print("Marketplace feed loaded.") 

                # Apply sorting and filtering
                self.apply_sorting_and_filtering(driver) 

                # Initialize prices
                all_prices = self.initialize_prices() 

                # Scroll to top and wait
                driver.execute_script("window.scrollTo(0, 0);") 
                time.sleep(2) 

                # Find all listing elements
                listing_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'x78zum5 xdt5ytf x1n2onr6')]//a[contains(@href, '/marketplace/item/')]")

                # NEW Collection Logic with duplicate prevention
                new_urls_added = 0
                for element in listing_elements:
                    try:
                        url = element.get_attribute('href')
                        if url and url not in scanned_urls and url not in listing_queue:
                            listing_queue.append(url)
                            new_urls_added += 1
                    except Exception as e:
                        print(f"Error processing listing element: {str(e)}")
                        continue

                print(f"Added {new_urls_added} new URLs to queue. Total queue size: {len(listing_queue)}")

                if not listing_elements: 
                    print("🚨 No listings found. Waiting for new listings to load...") 
                    time.sleep(5)  
                    continue

                # Process listings from queue
                while listing_queue:
                    if listings_scanned >= MAX_LISTINGS_TO_SCAN:
                        break
                    try:
                        # Get next URL from queue
                        listing_url = listing_queue.pop(0)
                        print(f"Processing listing {visible_listings_scanned + 1}: {listing_url}")
                        print(f"Remaining listings in queue: {len(listing_queue)}")
                        
                        # Skip if already scanned (double-check)
                        if listing_url in scanned_urls:
                            print(f"Skipping already scanned URL: {listing_url}")
                            continue
                        listing_id_url = self.extract_item_id(listing_url)
                    
                        try:
                            with open('listing_ids.txt', 'r') as f:
                                existing_ids = f.read().splitlines()
                            
                            if listing_id_url in existing_ids:
                                print('DUPLICATE FOUND')
                                consecutive_duplicate_count += 1
                        except Exception as e:
                            print(f"Error in determing if duplicate listing ID: {str(e)}")
                        try:
                            with open('listing_ids.txt', 'a') as f:
                                f.write(f"{listing_id_url}\n")
                            print(f"Saved listing ID: {listing_id_url}")
                        except Exception as e:
                            print(f"Error saving listing ID: {str(e)}")

                        if consecutive_duplicate_count >= 1:  
                            print(f"Consecutive duplicate count: {consecutive_duplicate_count}") 

                            if consecutive_duplicate_count >= 2: 
                                print(f"Detected 2 consecutive duplicates. Waiting for {WAIT_TIME_AFTER_REFRESH} seconds before refreshing.") 
                                time.sleep(WAIT_TIME_AFTER_REFRESH) 
                                consecutive_duplicate_count = 0 
                                break

                            continue
                        else:
                            
                            consecutive_duplicate_count = 0 

                        # Open new window and process listing
                        driver.execute_script("window.open('');") 
                        driver.switch_to.window(driver.window_handles[-1]) 

                        try: 
                            driver.get(listing_url) 
                            listing_info = self.extract_listing_info(driver, listing_url) 

                            
                            listing_info["url"] = listing_url

                            # Unified processing logic
                            if SHOW_ALL_LISTINGS or (not SHOW_ALL_LISTINGS and "Listing is suitable" in self.check_listing_suitability(listing_info)):
                                suitability_result = self.check_listing_suitability(listing_info)
                                profit_suitability, suitability_reason = self.process_suitable_listing(listing_info, all_prices, listings_scanned)
                                suitability_reason = suitability_result if not SHOW_ALL_LISTINGS else "Processed (SHOW_ALL_LISTINGS is True)"

                            if FAILURE_REASON_LISTED: 
                                self.write_to_file(f"\nListing {visible_listings_scanned + 1}: {listing_url}") 
                                self.write_to_file(f"Suitability: {suitability_reason}") 

                            # Mark URL as scanned
                            scanned_urls.append(listing_url)
                            
                            # Write scanned URL to file
                            with open(scanned_urls_file, 'a') as f: 
                                f.write(f"{listing_url}\n") 

                            listings_scanned += 1  
                            visible_listings_scanned += 1

                        except Exception as e:
                            print(f"An unexpected error occurred {str(e)}")
                            continue
                        finally: 
                            driver.close() 
                            driver.switch_to.window(main_window) 
                            
                            # Find new listing elements AFTER processing current listing
                            try:
                                new_listing_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'x78zum5 xdt5ytf x1n2onr6')]//a[contains(@href, '/marketplace/item/')]")
                                
                                # Counter to track new unique URLs
                                new_unique_urls_added = 0
                                
                                # Add only truly new URLs
                                for element in new_listing_elements:
                                    try:
                                        url = element.get_attribute('href')
                                        if url and url not in scanned_urls and url not in listing_queue:
                                            listing_queue.append(url)
                                            new_unique_urls_added += 1
                                    except Exception as e:
                                        print(f"Error processing new listing element: {str(e)}")
                                
                                print(f"Added {new_unique_urls_added} new unique URLs to queue. Total queue: {len(listing_queue)}")
                            
                            except Exception as e:
                                print(f"Error finding new listings: {e}")
                            
                            # Scroll periodically to load more listings
                            if listings_scanned % 10 == 0:  # Every 6 listings
                                self.scroll_page(driver, scroll_times=1)  # Scroll once
                    except Exception as e:
                        print(f"Error processing listing: {str(e)}")
                    # Break out if no more listings in queue
                    if not listing_queue:
                        print("Listing queue is empty. Breaking search loop.")
                        break

            except Exception as e:
                print(f"Error during searching: {str(e)}") 
                time.sleep(5)

    def apply_sorting_and_filtering(self, driver):
        """Apply sorting and filtering options on the marketplace."""
        try:
            # Sort by newest
            sort_by_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Sort by']"))
            )
            driver.execute_script("arguments[0].click();", sort_by_button)
            newest_first_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Date listed: Newest first']"))
            )
            driver.execute_script("arguments[0].click();", newest_first_option)
            time.sleep(2)

            # Filter by last 24 hours
            date_listed_dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'x1lliihq') and text()='Date listed']"))
            )
            driver.execute_script("arguments[0].click();", date_listed_dropdown)
            last_24_hours_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'x1lliihq') and text()='Last 24 hours']"))
            )
            driver.execute_script("arguments[0].click();", last_24_hours_option)
            time.sleep(2)
        except Exception as e:
            print(f"Error applying filters: {str(e)}")


    def extract_element_text_with_timeout(self, driver, selectors, element_name, timeout=element_exractor_timeout):
        print(f"Attempting to extract {element_name} with {timeout}s timeout...")
        for selector in selectors:
            try:
                element = WebDriverWait(driver, element_exractor_timeout).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                text = element.text.strip()
                if text:
                    print(f"Successfully extracted {element_name}: {text}")
                    return text
            except (TimeoutException, Exception) as e:
                print(f"Error with {element_name}")
        print(f"{element_name} not found within {element_exractor_timeout}s")
        return f"{element_name} not found"

    def extract_listing_info(self, driver, url):
        # Extract the listing ID from the URL

        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        raw_title = self.extract_element_text_with_timeout(driver, [
            "//h1[@aria-hidden='false']//span[contains(@class, 'x193iq5w') and contains(@class, 'xeuugli') and contains(@class, 'x13faqbe')]",
            "//h1[@aria-hidden='false']//span[contains(@class, 'x193iq5w') and contains(@class, 'xeuugli')]",
            "//h1[@aria-hidden='false']//span"
        ], "title")
        raw_description = self.extract_element_text_with_timeout(driver, ["//div[contains(@class, 'xz9dl7a x4uap5 xsag5q8')]//span[contains(@class, 'x193iq5w')]"], "description")

        listing_info = {
            "image_urls": self.extract_listing_images(driver),
            "title": raw_title.lower(),
            "description": raw_description.lower(),
            "join_date": self.extract_element_text_with_timeout(driver, ["//span[contains(@class, 'x193iq5w') and contains(@class, 'x1yc453h') and contains(text(), 'Joined Facebook')]", "//span[contains(text(), 'Joined Facebook')]"], "join_date"),
            "posting_date": self.extract_element_text_with_timeout(driver, ["//span[contains(@class, 'x193iq5w') and contains(@class, 'xeuugli') and contains(text(), 'Listed')]//span[@aria-hidden='true']", "//span[contains(text(), 'Listed')]//span[@aria-hidden='true']", "//span[contains(@class, 'x193iq5w') and contains(@class, 'xeuugli') and contains(text(), 'Listed')]"], "posting_date"),
        }
        
        if "see more" in listing_info["title"]:
            listing_info["title"] = listing_info["title"][:listing_info["title"].find("see more")]
        if len(listing_info["title"]) > 100:
            listing_info["title"] = listing_info["title"][:97] + "..."

        listing_info["posting_date"] = self.convert_to_minutes(listing_info["posting_date"]) if listing_info["posting_date"] != "posting_date not found" else max_posting_age_minutes + 1

        try:
            price_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.x193iq5w.xeuugli.x13faqbe.x1vvkbs.x1xmvt09.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.xudqn12.x676frb.x1lkfr7t.x1lbecb7.xk50ysn.xzsf02u")))
            raw_price = re.sub(r'[^\d.]', '', price_element.text.split('Â·')[0].strip())
            
            if raw_price and raw_price != "0":
                # New price truncation logic
                if len(raw_price) > 3:
                    raw_price = raw_price[:3]  # Take the first 3 digits
                
                multiplied_price = float(raw_price) * price_mulitplier
                listing_info["price"] = str(multiplied_price)
            else:
                listing_info["price"] = "0"
        except:
            listing_info["price"] = "0"

        listing_info["expected_revenue"] = None
        listing_info["profit"] = None
        listing_info["detected_items"] = {}
        listing_info["processed_images"] = self.download_and_process_images(listing_info["image_urls"])

        return listing_info

    def extract_element_text(self, driver, selectors, element_name):
        print(f"Attempting to extract {element_name}...")
        for selector in selectors:
            try:
                element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, selector)))
                text = element.text.strip()
                if text:
                    print(f"Successfully extracted {element_name}: {text}")
                    return text
            except Exception as e:
                print(f"Error extracting {element_name} with selector {selector}: {str(e)}")
        
        print(f"{element_name} not found")
        return f"{element_name} not found"

    def extract_listing_images(self, driver):
        try:
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.x5yr21d.xl1xv1r.xh8yej3")))
            return list(set(img.get_attribute("src") for img in driver.find_elements(By.CSS_SELECTOR, "img.x5yr21d.xl1xv1r.xh8yej3")))
        except Exception as e:
            print(f"Error in image extraction: {str(e)}")
            return []

    def convert_to_minutes(self, time_str):
        time_units = {
            'minute': 1, 'hour': 60, 'day': 1440,
            'week': 10080, 'month': 43200, 'year': 525600
        }
        for unit, multiplier in time_units.items():
            if unit in time_str:
                match = re.search(r'\d+', time_str)
                if match:
                    count = int(match.group())
                else:
                    count = 1 if f'a {unit}' in time_str else 0
                return count * multiplier
        return 0

    def check_listing_suitability(self, listing_info):
        checks = [
            
            (lambda: any(word in listing_info["title"].lower() for word in title_forbidden_words),
            "Title contains forbidden words"),
            (lambda: not any(word in listing_info["title"].lower() for word in title_must_contain),
            "Title does not contain any required words"),
            (lambda: any(word in listing_info["description"].lower() for word in description_forbidden_words),
            "Description contains forbidden words"),
            (lambda: "join_date not found" not in listing_info["join_date"].lower() and 
                    int(listing_info["join_date"].split()[-1]) == 2025,
            "Seller joined Facebook in 2025"),
            (lambda: listing_info["price"] != "Price not found" and 
                    (float(listing_info["price"]) < min_price or float(listing_info["price"]) > max_price),
            f"Price £{listing_info['price']} is outside the range £{min_price}-£{max_price}"),
            (lambda: len(re.findall(r'[£$]\s*\d+|\d+\s*[£$]', listing_info["description"])) >= 3,
            "Too many $ symbols"),
            (lambda: float(listing_info["price"]) in BANNED_PRICES,
            "Price in banned prices"),
        ]
        for check, message in checks:
            try:
                if check():
                    return f"Unsuitable: {message}"
            except (ValueError, IndexError, AttributeError, TypeError):
                if "price" in message:
                    return "Unsuitable: Unable to parse price"
                if "posting_date" in message:
                    return "Unsuitable: Unable to parse posting date"
                continue

        return "Listing is suitable"

    def save_image(self, image_url, save_path):
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                with open(save_path, 'wb') as file:
                    file.write(response.content)
                saved_images = 0
                saved_images + 1
                return True
            else:
                print(f"Failed to download image. Status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"Error saving image: {str(e)}")
            return False

    def perform_detection_on_listing_images(self, model, listing_dir):
        """
        Enhanced object detection with all Facebook exceptions and logic
        MODIFIED: All game classes are now capped at 1 per listing
        """
        if not os.path.isdir(listing_dir):
            return {}, []

        detected_objects = {class_name: [] for class_name in CLASS_NAMES}
        processed_images = []
        confidences = {item: 0 for item in ['switch', 'oled', 'lite', 'switch_box', 'oled_box', 'lite_box', 'switch_in_tv', 'oled_in_tv']}

        image_files = [f for f in os.listdir(listing_dir) if f.endswith('.png')]
        if not image_files:
            return {class_name: 0 for class_name in CLASS_NAMES}, processed_images

        for image_file in image_files:
            image_path = os.path.join(listing_dir, image_file)
            try:
                img = cv2.imread(image_path)
                if img is None:
                    continue

                # Track detections for this image
                image_detections = {class_name: 0 for class_name in CLASS_NAMES}
                results = model(img, verbose=False)
                
                for result in results:
                    for box in result.boxes.cpu().numpy():
                        class_id = int(box.cls[0])
                        confidence = box.conf[0]
                        
                        if class_id < len(CLASS_NAMES):
                            class_name = CLASS_NAMES[class_id]
                            min_confidence = HIGHER_CONFIDENCE_ITEMS.get(class_name, GENERAL_CONFIDENCE_MIN)
                            
                            if confidence >= min_confidence:
                                if class_name in ['switch', 'oled', 'lite', 'switch_box', 'oled_box', 'lite_box', 'switch_in_tv', 'oled_in_tv']:
                                    confidences[class_name] = max(confidences[class_name], confidence)
                                else:
                                    image_detections[class_name] += 1
                                
                                # Draw bounding box
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(img, f"{class_name} ({confidence:.2f})", (x1, y1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.625, (0, 255, 0), 2)

                # Update overall detected objects with max from this image
                for class_name, count in image_detections.items():
                    detected_objects[class_name].append(count)

                # Convert to PIL Image for pygame compatibility
                processed_images.append(Image.fromarray(cv2.cvtColor(
                    cv2.copyMakeBorder(img, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=[0, 0, 0]),
                    cv2.COLOR_BGR2RGB)))

            except Exception as e:
                print(f"Error processing image {image_path}: {str(e)}")
                continue

        # Convert lists to max values
        final_detected_objects = {class_name: max(counts) if counts else 0 for class_name, counts in detected_objects.items()}
        
        # Handle mutually exclusive items
        final_detected_objects = self.handle_mutually_exclusive_items_vinted(final_detected_objects, confidences)
        
        # NEW CODE: Cap all game classes at 1 per listing
        # Define the game classes that need to be capped
        game_classes_to_cap = [
            '1_2_switch', 'animal_crossing', 'arceus_p', 'bow_z', 'bros_deluxe_m', 'crash_sand',
            'dance', 'diamond_p', 'evee', 'fifa_23', 'fifa_24', 'gta', 'just_dance', 'kart_m', 'kirby',
            'lets_go_p', 'links_z', 'luigis', 'mario_maker_2', 'mario_sonic', 'mario_tennis', 'minecraft',
            'minecraft_dungeons', 'minecraft_story', 'miscellanious_sonic', 'odyssey_m', 'other_mario',
            'party_m', 'rocket_league', 'scarlet_p', 'shield_p', 'shining_p', 'skywards_z', 'smash_bros',
            'snap_p', 'splatoon_2', 'splatoon_3', 'super_m_party', 'super_mario_3d', 'switch_sports',
            'sword_p', 'tears_z', 'violet_p'
        ]
        
        # Cap each game class at maximum 1
        games_capped = []
        for game_class in game_classes_to_cap:
            if final_detected_objects.get(game_class, 0) > 1:
                original_count = final_detected_objects[game_class]
                final_detected_objects[game_class] = 1
                games_capped.append(f"{game_class}: {original_count} -> 1")
        
        # Print capping information if any games were capped
        if games_capped:
            print(f"🎮 GAMES CAPPED: {', '.join(games_capped)}")
        
        return final_detected_objects, processed_images

    def fetch_price(self, class_name):
        if class_name in ['lite_box', 'oled_box', 'oled_in_tv', 'switch_box', 'switch_in_tv', 'other_mario']:
            return None
        price = BASE_PRICES.get(class_name, 0)
        delivery_cost = 5.0 if class_name in ['lite', 'oled', 'switch'] else 3.5
        final_price = price + delivery_cost
        return final_price

    def fetch_all_prices(self):
        all_prices = {class_name: self.fetch_price(class_name) for class_name in class_names if self.fetch_price(class_name) is not None}
        all_prices.update({
            'lite_box': all_prices.get('lite', 0) * 1.05, 
            'oled_box': all_prices.get('oled', 0) + all_prices.get('comfort_h', 0) + all_prices.get('tv_white', 0) - 15, 
            'oled_in_tv': all_prices.get('oled', 0) + all_prices.get('tv_white', 0) - 10, 
            'switch_box': all_prices.get('switch', 0) + all_prices.get('comfort_h', 0) + all_prices.get('tv_black', 0) - 5, 
            'switch_in_tv': all_prices.get('switch', 0) + all_prices.get('tv_black', 0) - 3.5, 
            'other_mario': 22.5,
            'anonymous_games': 5  # Add price for anonymous games
        })
        return all_prices

    def check_profit_suitability(self, listing_price, profit_percentage):
        if 10 <= listing_price < 16:
            return 100 <= profit_percentage <= 600 #50
        elif 16 <= listing_price < 25:
            return 65 <= profit_percentage <= 400 #50
        elif 25 <= listing_price < 50:
            return 37.5 <= profit_percentage <= 550 #35
        elif 50 <= listing_price < 100:
            return 35 <= profit_percentage <= 500 #32.5
        elif listing_price >= 100:
            return 30 <= profit_percentage <= 450 # 30
        else:
            return False

    def calculate_revenue(self, detected_objects, all_prices, listing_price, listing_title, listing_description):
        # List of game-related classes
        game_classes = [
    '1_2_switch', 'animal_crossing', 'arceus_p', 'bow_z', 'bros_deluxe_m', 'crash_sand',
    'dance', 'diamond_p', 'evee', 'fifa_23', 'fifa_24', 'gta','just_dance', 'kart_m', 'kirby',
    'lets_go_p', 'links_z', 'luigis', 'mario_maker_2', 'mario_sonic', 'mario_tennis', 'minecraft',
    'minecraft_dungeons', 'minecraft_story', 'miscellanious_sonic', 'odyssey_m', 'other_mario',
    'party_m', 'rocket_league', 'scarlet_p', 'shield_p', 'shining_p', 'skywards_z', 'smash_bros',
    'snap_p', 'splatoon_2', 'splatoon_3', 'super_m_party', 'super_mario_3d', 'switch_sports',
    'sword_p', 'tears_z', 'violet_p'
    ]
        
        # Count detected games
        detected_games_count = sum(detected_objects.get(game, 0) for game in game_classes)
        
        # Find highest number before "games" in title and description
        def extract_games_number(text):
        # Prioritize specific game type matches first
            matches = (
                re.findall(r'(\d+)\s*(switch|nintendo)\s*games', text.lower()) +  # Switch/Nintendo specific
                re.findall(r'(\d+)\s*games', text.lower())  # Generic games
            )
            
            # Convert matches to integers and find the maximum
            numeric_matches = [int(match[0]) if isinstance(match, tuple) else int(match) for match in matches]
            
            return max(numeric_matches) if numeric_matches else 0
        
        title_games = extract_games_number(listing_title)
        desc_games = extract_games_number(listing_description)
        text_games_count = max(title_games, desc_games)
        
        # Calculate miscellaneous games
        misc_games_count = max(0, text_games_count - detected_games_count)
        misc_games_revenue = misc_games_count * miscellaneous_games_price
        
        adjustments = {
            'oled_box': ['switch', 'comfort_h', 'tv_white'],
            'switch_box': ['switch', 'comfort_h', 'tv_black'],
            'lite_box': ['lite']
        }

        for box, items in adjustments.items():
            box_count = detected_objects.get(box, 0)
            for item in items:
                detected_objects[item] = max(0, detected_objects.get(item, 0) - box_count)
        detected_objects.pop('switch_screen', None)

        display_objects = detected_objects.copy()

        sd_card_keywords = SD_CARD_WORD
        title_lower = listing_title.lower()
        desc_lower = listing_description.lower()

        sd_card_present = any(keyword in title_lower or keyword in desc_lower for keyword in sd_card_keywords)

        total_revenue = misc_games_revenue

        if sd_card_present:
            total_revenue += sd_card_revenue
            print(f"SD Card detected: Added £{sd_card_revenue} to revenue")

        for item, count in detected_objects.items():
            # Safely handle both string and integer counts
            if isinstance(count, str):
                count_match = re.match(r'(\d+)', count)
                count = int(count_match.group(1)) if count_match else 0
            
            item_price = all_prices.get(item, 0)
            if item == 'controller' and 'pro' in listing_title.lower() and count > 0:
                pro_price = item_price + 7.50
                total_revenue += pro_price * count
            else:
                total_revenue += item_price * count
        
        print("\nRevenue Breakdown:")
        for item, count in detected_objects.items():
            # Safely handle both string and integer counts
            if isinstance(count, str):
                count_match = re.match(r'(\d+)', count)
                count = int(count_match.group(1)) if count_match else 0
            
            if item in all_prices:
                base_price = all_prices[item]
                if item == 'controller' and 'pro' in listing_title.lower() and count > 0:
                    item_revenue = (base_price + 7.50) * count
                else:
                    item_revenue = base_price * count
            else:
                print(f"Cannot calculate price for {item}. Price not found.")
        
        if misc_games_count > 0:
            print(f"Miscellaneous games: {misc_games_count} x £{miscellaneous_games_price:.2f} = £{misc_games_revenue:.2f}")

        expected_profit = total_revenue - listing_price
        profit_percentage = (expected_profit / listing_price) * 100 if listing_price > 0 else 0

        print(f"Listing Price: £{listing_price:.2f}")
        print(f"Total Expected Revenue: £{total_revenue:.2f}")
        print(f"Expected Profit/Loss: £{expected_profit:.2f} ({profit_percentage:.2f}%)")

        controller_count = detected_objects.get('controller', 0)
        if controller_count > 0:
            item_price = all_prices.get('controller', 0)
            if 'pro' in listing_title.lower():
                pro_price = item_price + 7.50
                total_revenue += pro_price * controller_count
        
        # Remove controller from detected_objects before returning

        return total_revenue, expected_profit, profit_percentage, display_objects

    def write_listing_to_file(self, output_file_path, listing_info, suitability_result):
        with open(output_file_path, 'a') as f:
            if SHOW_ALL_LISTINGS or "Listing is suitable" in suitability_result:
                f.write(f"Listing {listing_info['unique_id']}: {listing_info['url']} Price: £{listing_info['price']}, Expected revenue: £{listing_info.get('expected_revenue', 0):.2f} ")
                if listing_info.get('detected_items'):
                    f.write("Detected items: ")
                    for item, count in listing_info['detected_items'].items():
                        f.write(f"{item}={count} ")
                f.write(f"Suitability: {suitability_result}\n")
            else:
                f.write(f"Listing {listing_info['unique_id']} was unsuitable: {suitability_result} {listing_info['url']}\n")

    def initialize_prices(self):
        return self.fetch_all_prices()

    def run(self):
        global scraper_instance
        scraper_instance = self
        global driver, messaging_driver, current_listing_url  # Add current_listing_url to globals

        if setup_website:
            print("Setting up Cloudflare Tunnel website tunnel...")
            # Since run_flask_app() now integrates Cloudflare Tunnel (via cloudflared),
            # you don't need to call a separate tunnel setup function here.
            # (Any additional Cloudflare initialization code could go here if needed.)

        self.clear_output_file()

        # Start the Flask app in a separate thread
        flask_thread = threading.Thread(target=self.run_flask_app)
        flask_thread.daemon = True
        flask_thread.start()

        pygame_thread = threading.Thread(target=self.run_pygame_window)
        pygame_thread.start()

        # Set up two separate drivers
        driver = None
        messaging_driver = None

        try:
            # Setup Chrome Profile Driver for scraping
            driver = self.setup_chrome_profile_driver()

            # Setup a second, separate Chrome Driver for messaging
            messaging_driver = self.setup_chrome_messaging_driver()

            if messaging_driver is None:
                print("Failed to initialize messaging driver. Exiting.")
                return
            
            driver_restart_thread = threading.Thread(target=self.periodically_restart_messaging_driver, daemon=True)
            driver_restart_thread.start()

            print("Logging in to Facebook on second driver...")
            self.login_to_facebook(driver)

            all_prices = self.initialize_prices()

            # Initialize current_listing_url
            current_listing_url = ""

            self.update_listing_details("", "", "", "0", None, None, {}, [], None)

            print(f"Searching for listings with query: {search_query}")
            self.search_and_select_listings(driver, search_query, OUTPUT_FILE_PATH)

        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            if driver:
                driver.quit()
            if messaging_driver:
                messaging_driver.quit()

class VintedScraper:
    # Add this method to the VintedScraper class
    def send_pushover_notification(self, title, message, api_token, user_key):
        """
        Send a notification via Pushover
        :param title: Notification title
        :param message: Notification message
        :param api_token: Pushover API token
        :param user_key: Pushover user key
        """
        try:
            url = "https://api.pushover.net/1/messages.json"
            payload = {
                "token": api_token,
                "user": user_key,
                "title": title,
                "message": message
            }
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                print(f"Notification sent successfully: {title}")
            else:
                print(f"Failed to send notification. Status code: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error sending Pushover notification: {str(e)}")

    def fetch_price(self, class_name):
        if class_name in ['lite_box', 'oled_box', 'oled_in_tv', 'switch_box', 'switch_in_tv', 'other_mario']:
            return None
        price = BASE_PRICES.get(class_name, 0)
        delivery_cost = 5.0 if class_name in ['lite', 'oled', 'switch'] else 3.5
        final_price = price + delivery_cost
        return final_price
    def fetch_all_prices(self):
        all_prices = {class_name: self.fetch_price(class_name) for class_name in class_names if self.fetch_price(class_name) is not None}
        all_prices.update({
            'lite_box': all_prices.get('lite', 0) * 1.05, 
            'oled_box': all_prices.get('oled', 0) + all_prices.get('comfort_h', 0) + all_prices.get('tv_white', 0) - 15, 
            'oled_in_tv': all_prices.get('oled', 0) + all_prices.get('tv_white', 0) - 10, 
            'switch_box': all_prices.get('switch', 0) + all_prices.get('comfort_h', 0) + all_prices.get('tv_black', 0) - 5, 
            'switch_in_tv': all_prices.get('switch', 0) + all_prices.get('tv_black', 0) - 3.5, 
            'other_mario': 22.5,
            'anonymous_games': 5  # Add price for anonymous games
        })
        return all_prices
    def __init__(self):
        # Initialize pygame-related variables similar to FacebookScraper
        global current_listing_title, current_listing_description, current_listing_join_date, current_listing_price
        global current_expected_revenue, current_profit, current_detected_items, current_listing_images
        global current_bounding_boxes, current_listing_url, current_suitability, suitable_listings
        global current_listing_index, recent_listings
        
        # **CRITICAL FIX: Initialize recent_listings for website navigation**
        recent_listings = {
            'listings': [],
            'current_index': 0
        }
        
        # Initialize all current listing variables
        current_listing_title = "No title"
        current_listing_description = "No description"
        current_listing_join_date = "No join date"
        current_listing_price = "0"
        current_expected_revenue = "0"
        current_profit = "0"
        current_detected_items = "None"
        current_listing_images = []
        current_bounding_boxes = {}
        current_listing_url = ""
        current_suitability = "Suitability unknown"
        suitable_listings = []
        current_listing_index = 0

        self.vinted_button_queue = queue.Queue()
        self.vinted_processing_active = threading.Event()  # To track if we're currently processing
        self.main_driver = None

    def run_pygame_window(self):
        global LOCK_POSITION, current_listing_index, suitable_listings
        screen, clock = self.initialize_pygame_window()
        rectangles = [pygame.Rect(*rect) for rect in self.load_rectangle_config()] if self.load_rectangle_config() else [
            pygame.Rect(0, 0, 240, 180), pygame.Rect(240, 0, 240, 180), pygame.Rect(480, 0, 320, 180),
            pygame.Rect(0, 180, 240, 180), pygame.Rect(240, 180, 240, 180), pygame.Rect(480, 180, 320, 180),
            pygame.Rect(0, 360, 240, 240), pygame.Rect(240, 360, 240, 120), pygame.Rect(240, 480, 240, 120),
            pygame.Rect(480, 360, 160, 240), pygame.Rect(640, 360, 160, 240)
        ]
        fonts = {
            'number': pygame.font.Font(None, 24),
            'price': pygame.font.Font(None, 36),
            'title': pygame.font.Font(None, 40),
            'description': pygame.font.Font(None, 28),
            'join_date': pygame.font.Font(None, 28),
            'revenue': pygame.font.Font(None, 36),
            'profit': pygame.font.Font(None, 36),
            'items': pygame.font.Font(None, 30),
            'click': pygame.font.Font(None, 28),
            'suitability': pygame.font.Font(None, 28),
            'reviews': pygame.font.Font(None, 28)  # New font for seller reviews
        }
        dragging = False
        resizing = False
        drag_rect = None
        drag_offset = (0, 0)
        resize_edge = None

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_l:
                        LOCK_POSITION = not LOCK_POSITION
                    elif event.key == pygame.K_RIGHT:
                        if suitable_listings:
                            current_listing_index = (current_listing_index + 1) % len(suitable_listings)
                            self.update_listing_details(**suitable_listings[current_listing_index])
                    elif event.key == pygame.K_LEFT:
                        if suitable_listings:
                            current_listing_index = (current_listing_index - 1) % len(suitable_listings)
                            self.update_listing_details(**suitable_listings[current_listing_index])
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        # Check if rectangle 4 was clicked
                        if rectangles[3].collidepoint(event.pos):
                            if suitable_listings and 0 <= current_listing_index < len(suitable_listings):
                                current_url = suitable_listings[current_listing_index].get('url')
                                if current_url:
                                    try:
                                        import webbrowser
                                        webbrowser.open(current_url)
                                    except Exception as e:
                                        print(f"Failed to open URL: {e}")
                        elif not LOCK_POSITION:
                            for i, rect in enumerate(rectangles):
                                if rect.collidepoint(event.pos):
                                    if event.pos[0] > rect.right - 10 and event.pos[1] > rect.bottom - 10:
                                        resizing = True
                                        drag_rect = i
                                        resize_edge = 'bottom-right'
                                    else:
                                        dragging = True
                                        drag_rect = i
                                        drag_offset = (rect.x - event.pos[0], rect.y - event.pos[1])
                                    break
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        dragging = False
                        resizing = False
                        drag_rect = None
            
            # Handle dragging and resizing
            if dragging and drag_rect is not None:
                rectangles[drag_rect].x = pygame.mouse.get_pos()[0] + drag_offset[0]
                rectangles[drag_rect].y = pygame.mouse.get_pos()[1] + drag_offset[1]
            elif resizing and drag_rect is not None:
                if resize_edge == 'bottom-right':
                    width = max(pygame.mouse.get_pos()[0] - rectangles[drag_rect].left, 20)
                    height = max(pygame.mouse.get_pos()[1] - rectangles[drag_rect].top, 20)
                    rectangles[drag_rect].size = (width, height)
            
            screen.fill((204, 210, 255))
            for i, rect in enumerate(rectangles):
                pygame.draw.rect(screen, (0, 0, 0), rect, 2)
                number_text = fonts['number'].render(str(i + 1), True, (255, 0, 0))
                number_rect = number_text.get_rect(topright=(rect.right - 5, rect.top + 5))
                screen.blit(number_text, number_rect)

                if i == 2:  # Rectangle 3 (index 2) - Title
                    self.render_text_in_rect(screen, fonts['title'], current_listing_title, rect, (0, 0, 0))
                elif i == 1:  # Rectangle 2 (index 1) - Price
                    self.render_text_in_rect(screen, fonts['price'], current_listing_price, rect, (0, 0, 255))
                elif i == 7:  # Rectangle 8 (index 7) - Description
                    self.render_multiline_text(screen, fonts['description'], current_listing_description, rect, (0, 0, 0))
                elif i == 8:  # Rectangle 9 (index 8) - Upload Date
                    self.render_text_in_rect(screen, fonts['join_date'], current_listing_join_date, rect, (0, 0, 0))
                elif i == 4:  # Rectangle 5 (index 4) - Expected Revenue
                    self.render_text_in_rect(screen, fonts['revenue'], current_expected_revenue, rect, (0, 128, 0))
                elif i == 9:  # Rectangle 10 (index 9) - Profit
                    self.render_text_in_rect(screen, fonts['profit'], current_profit, rect, (128, 0, 128))
                elif i == 0:  # Rectangle 1 (index 0) - Detected Items
                    self.render_multiline_text(screen, fonts['items'], current_detected_items, rect, (0, 0, 0))
                elif i == 10:  # Rectangle 11 (index 10) - Images
                    self.render_images(screen, current_listing_images, rect, current_bounding_boxes)
                elif i == 3:  # Rectangle 4 (index 3) - Click to open
                    click_text = "CLICK TO OPEN LISTING IN CHROME"
                    self.render_text_in_rect(screen, fonts['click'], click_text, rect, (255, 0, 0))
                elif i == 5:  # Rectangle 6 (index 5) - Suitability Reason
                    self.render_text_in_rect(screen, fonts['suitability'], current_suitability, rect, (255, 0, 0) if "Unsuitable" in current_suitability else (0, 255, 0))
                elif i == 6:  # Rectangle 7 (index 6) - NEW: Seller Reviews
                    self.render_text_in_rect(screen, fonts['reviews'], current_seller_reviews, rect, (0, 0, 128))  # Dark blue color

            screen.blit(fonts['title'].render("LOCKED" if LOCK_POSITION else "UNLOCKED", True, (255, 0, 0) if LOCK_POSITION else (0, 255, 0)), (10, 10))

            if suitable_listings:
                listing_counter = fonts['number'].render(f"Listing {current_listing_index + 1}/{len(suitable_listings)}", True, (0, 0, 0))
                screen.blit(listing_counter, (10, 40))

            pygame.display.flip()
            clock.tick(30)

        self.save_rectangle_config(rectangles)
        pygame.quit()
        
    def base64_encode_image(self, img):
        """Convert PIL Image to base64 string, resizing if necessary"""
        # Resize image while maintaining aspect ratio
        max_size = (200, 200)
        img.thumbnail(max_size, Image.LANCZOS)
        
        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def render_images(self, screen, images, rect, bounding_boxes):
        if not images:
            return

        num_images = len(images)
        if num_images == 1:
            grid_size = 1
        elif 2 <= num_images <= 4:
            grid_size = 2
        else:
            grid_size = 3

        cell_width = rect.width // grid_size
        cell_height = rect.height // grid_size

        for i, img in enumerate(images):
            if i >= grid_size * grid_size:
                break
            row = i // grid_size
            col = i % grid_size
            img = img.resize((cell_width, cell_height))
            img_surface = pygame.image.fromstring(img.tobytes(), img.size, img.mode)
            screen.blit(img_surface, (rect.left + col * cell_width, rect.top + row * cell_height))

        # Display suitability reason
        if FAILURE_REASON_LISTED:
            font = pygame.font.Font(None, 24)
            suitability_text = font.render(current_suitability, True, (255, 0, 0) if "Unsuitable" in current_suitability else (0, 255, 0))
            screen.blit(suitability_text, (rect.left + 10, rect.bottom - 30))

    def initialize_pygame_window(self):
        pygame.init()
        screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        pygame.display.set_caption("Facebook Marketplace Scanner")
        return screen, pygame.time.Clock()

    def load_rectangle_config(self):
        return json.load(open(CONFIG_FILE, 'r')) if os.path.exists(CONFIG_FILE) else None

    def save_rectangle_config(self, rectangles):
        json.dump([(rect.x, rect.y, rect.width, rect.height) for rect in rectangles], open(CONFIG_FILE, 'w'))

    def render_text_in_rect(self, screen, font, text, rect, color):
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_width, _ = font.size(test_line)
            if test_width <= rect.width - 10:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        if current_line:
            lines.append(' '.join(current_line))

        total_height = sum(font.size(line)[1] for line in lines)
        if total_height > rect.height:
            scale_factor = rect.height / total_height
            new_font_size = max(1, int(font.get_height() * scale_factor))
            try:
                font = pygame.font.Font(None, new_font_size)  # Use default font
            except pygame.error:
                print(f"Error creating font with size {new_font_size}")
                return  # Skip rendering if font creation fails

        y = rect.top + 5
        for line in lines:
            try:
                text_surface = font.render(line, True, color)
                text_rect = text_surface.get_rect(centerx=rect.centerx, top=y)
                screen.blit(text_surface, text_rect)
                y += font.get_linesize()
            except pygame.error as e:
                print(f"Error rendering text: {e}")
                continue  # Skip this line if rendering fails

    def extract_price(self, text):
        """
        Extracts a float from a string like '£4.50' or '4.50 GBP'
        Returns 0.0 if nothing is found or text is None
        """
        if not text:
            return 0.0
        match = re.search(r"[\d,.]+", text)
        if match:
            return float(match.group(0).replace(",", ""))
        return 0.0
    
    def render_multiline_text(self, screen, font, text, rect, color):
        # Convert dictionary to formatted string if needed
        if isinstance(text, dict):
            text_lines = []
            for key, value in text.items():
                text_lines.append(f"{key}: {value}")
            text = '\n'.join(text_lines)
        
        # Rest of the existing function remains the same
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_width, _ = font.size(test_line)
            if test_width <= rect.width - 20:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        if current_line:
            lines.append(' '.join(current_line))

        total_height = sum(font.size(line)[1] for line in lines)
        if total_height > rect.height:
            scale_factor = rect.height / total_height
            new_font_size = max(1, int(font.get_height() * scale_factor))
            try:
                font = pygame.font.Font(None, new_font_size)  # Use default font
            except pygame.error:
                print(f"Error creating font with size {new_font_size}")
                return  # Skip rendering if font creation fails

        y_offset = rect.top + 10
        for line in lines:
            try:
                text_surface = font.render(line, True, color)
                text_rect = text_surface.get_rect(centerx=rect.centerx, top=y_offset)
                screen.blit(text_surface, text_rect)
                y_offset += font.get_linesize()
                if y_offset + font.get_linesize() > rect.bottom - 10:
                    break
            except pygame.error as e:
                print(f"Error rendering text: {e}")
                continue  # Skip this line if rendering fails
        
    def update_listing_details(self, title, description, join_date, price, expected_revenue, profit, detected_items, processed_images, bounding_boxes, url=None, suitability=None, seller_reviews=None):
        global current_listing_title, current_listing_description, current_listing_join_date, current_listing_price
        global current_expected_revenue, current_profit, current_detected_items, current_listing_images 
        global current_bounding_boxes, current_listing_url, current_suitability, current_seller_reviews

        # Close and clear existing image
        if 'current_listing_images' in globals():
            for img in current_listing_images:
                try:
                    img.close()  # Explicitly close the image
                except Exception as e:
                    print(f"Error closing image: {str(e)}")
            current_listing_images.clear()

        if processed_images:
            for img in processed_images:
                try:
                    img_copy = img.copy()  # Create a fresh copy
                    current_listing_images.append(img_copy)
                except Exception as e:
                    print(f"Error copying image: {str(e)}")
        
        # Store bounding boxes with more robust handling
        current_bounding_boxes = {
            'image_paths': bounding_boxes.get('image_paths', []) if bounding_boxes else [],
            'detected_objects': bounding_boxes.get('detected_objects', {}) if bounding_boxes else {}
        }

        # Handle detected_items for Box 1 - show raw detected objects with counts
        if isinstance(detected_items, dict):
            # Format as "item_name: count" for items with count > 0
            formatted_detected_items = {}
            for item, count in detected_items.items():
                try:
                    count_int = int(count) if isinstance(count, str) else count
                    if count_int > 0:
                        formatted_detected_items[item] = str(count_int)
                except (ValueError, TypeError):
                    continue
            
            if not formatted_detected_items:
                formatted_detected_items = {"no_items": "No items detected"}
        else:
            formatted_detected_items = {"no_items": "No items detected"}

        # Explicitly set the global variables
        current_detected_items = formatted_detected_items
        current_listing_title = title[:50] + '...' if len(title) > 50 else title
        current_listing_description = description[:200] + '...' if len(description) > 200 else description if description else "No description"
        current_listing_join_date = join_date if join_date else "Unknown upload date"
        current_listing_price = f"Price:\n£{float(price):.2f}" if price else "Price:\n£0.00"
        current_expected_revenue = f"Rev:\n£{expected_revenue:.2f}" if expected_revenue else "Rev:\n£0.00"
        current_profit = f"Profit:\n£{profit:.2f}" if profit else "Profit:\n£0.00"
        current_listing_url = url
        current_suitability = suitability if suitability else "Suitability unknown"
        current_seller_reviews = seller_reviews if seller_reviews else "No reviews yet"


    def vinted_button_clicked_enhanced(self, url):
        """
        Enhanced button click handler for Vinted with the requested functionality:
        1. Start a stopwatch
        2. Pause main scraping
        3. Open second driver
        4. Navigate to listing
        5. Wait 3 seconds
        6. Close second driver
        7. Continue main scraping
        """
        print(f"🔘 Vinted button clicked for: {url}")
        
        # Add to queue
        self.vinted_button_queue.put(url)
        
        # Start processing if not already active
        if not self.vinted_processing_active.is_set():
            processing_thread = threading.Thread(target=self.process_vinted_button_queue)
            processing_thread.daemon = True
            processing_thread.start()
        else:
            print("📋 Request added to queue (currently processing another request)")
    
    def process_vinted_button_queue(self):
        """
        Process the Vinted button request queue
        """
        self.vinted_processing_active.set()
        
        while not self.vinted_button_queue.empty():
            try:
                url = self.vinted_button_queue.get(timeout=1)
                self.handle_single_vinted_button_request(url)
                self.vinted_button_queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                print(f"❌ Error processing Vinted button request: {e}")
                continue
        
        self.vinted_processing_active.clear()
        print("✅ Vinted button queue processing complete")
    
    def handle_single_vinted_button_request(self, url):
        """
        Handle a single Vinted button request with all the specified requirements
        """
        print(f"🚀 Starting Vinted button request for: {url}")
        
        # 1. Start stopwatch
        start_time = time.time()
        
        # 2. Pause main scraping (signal to main driver if needed)
        print("⏸️ Pausing main scraping...")
        self.pause_main_scraping = True
        
        # 3. Open second driver on same account
        second_driver = None
        try:
            print("🌐 Opening second driver...")
            second_driver = self.setup_buying_driver()  # Use same setup as main driver
            
            # 4. Navigate to the listing link
            print(f"📍 Navigating to: {url}")
            second_driver.get(url)
            
            # Wait for page to load
            WebDriverWait(second_driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("✅ Page loaded successfully")
            
            # 5. Wait 3 seconds
            print("⏱️ Waiting 3 seconds...")
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ Error during second driver operation: {e}")
        finally:
            # 6. Close second driver
            if second_driver:
                try:
                    second_driver.quit()
                    print("🔒 Second driver closed")
                except Exception as e:
                    print(f"⚠️ Warning: Error closing second driver: {e}")
            
            # 7. Continue main scraping
            self.pause_main_scraping = False
            print("▶️ Resuming main scraping...")
        
        # Check if we hit the 10-second limit
        elapsed_time = time.time() - start_time
        if elapsed_time >= 10:
            print(f"⏰ Process completed at 10-second limit (actual: {elapsed_time:.2f}s)")
        else:
            print(f"✅ Process completed in {elapsed_time:.2f} seconds")
    
    def setup_driver(self):
        """
        Enhanced Chrome driver setup with better stability and crash prevention
        """
        chrome_opts = Options()
        
        # Basic preferences
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.popups": 0,
            "download.prompt_for_download": False,
        }
        chrome_opts.add_experimental_option("prefs", prefs)
        
        # User data directory setup
        chrome_opts.add_argument(f"--user-data-dir={PERMANENT_USER_DATA_DIR}")
        chrome_opts.add_argument(f"--profile-directory=Default")
        #profile 2 = pc
        # default = laptop
        
        # Core stability arguments
        chrome_opts.add_argument("--headless")
        chrome_opts.add_argument("--no-sandbox")
        chrome_opts.add_argument("--disable-dev-shm-usage")
        chrome_opts.add_argument("--disable-gpu")
        chrome_opts.add_argument("--disable-software-rasterizer")
        
        # Memory and process management
        chrome_opts.add_argument("--disable-background-timer-throttling")
        chrome_opts.add_argument("--disable-backgrounding-occluded-windows")
        chrome_opts.add_argument("--disable-renderer-backgrounding")
        chrome_opts.add_argument("--disable-features=TranslateUI,VizDisplayCompositor")
        chrome_opts.add_argument("--disable-ipc-flooding-protection")
        chrome_opts.add_argument("--disable-background-networking")
        chrome_opts.add_argument("--disable-default-apps")
        chrome_opts.add_argument("--disable-extensions")
        chrome_opts.add_argument("--disable-sync")
        chrome_opts.add_argument("--disable-translate")
        chrome_opts.add_argument("--hide-scrollbars")
        chrome_opts.add_argument("--mute-audio")
        chrome_opts.add_argument("--no-first-run")
        chrome_opts.add_argument("--disable-logging")
        chrome_opts.add_argument("--disable-permissions-api")
        chrome_opts.add_argument("--disable-web-security")
        
        # Critical for preventing crashes
        chrome_opts.add_argument("--disable-blink-features=AutomationControlled")
        chrome_opts.add_argument("--disable-dev-shm-usage")
        chrome_opts.add_argument("--remote-debugging-port=0")  # Let Chrome choose available port
        chrome_opts.add_argument("--disable-crash-reporter")
        chrome_opts.add_argument("--disable-component-update")
        chrome_opts.add_argument("--disable-domain-reliability")
        chrome_opts.add_argument("--disable-client-side-phishing-detection")
        chrome_opts.add_argument("--disable-hang-monitor")
        chrome_opts.add_argument("--disable-prompt-on-repost")
        chrome_opts.add_argument("--disable-background-mode")
        
        # Memory limits to prevent crashes
        chrome_opts.add_argument("--max_old_space_size=2048")
        chrome_opts.add_argument("--memory-pressure-off")
        
        # Window settings for headless mode
        chrome_opts.add_argument("--window-size=1280,720")
        chrome_opts.add_argument("--disable-infobars")
        
        # Logging control
        chrome_opts.add_argument("--log-level=3")
        chrome_opts.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        chrome_opts.add_experimental_option('useAutomationExtension', False)
        
        # Additional stability options
        chrome_opts.add_argument("--no-zygote")
        chrome_opts.add_argument("--single-process")  # Use single process to avoid multi-process crashes
        chrome_opts.add_argument("--disable-features=VizDisplayCompositor")
        
        try:
            service = Service(
                ChromeDriverManager().install(),
                log_path=os.devnull  # Suppress driver logs
            )
            
            # Add service arguments for additional stability
            service_args = [
                '--verbose=false',
                '--silent',
                '--log-level=3'
            ]
            
            print("🚀 Starting Chrome driver with enhanced stability settings...")
            driver = webdriver.Chrome(service=service, options=chrome_opts)
            
            # Set timeouts
            driver.implicitly_wait(10)
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            
            print("✅ Chrome driver initialized successfully")
            return driver
            
        except Exception as e:
            print(f"❌ CRITICAL: Chrome driver failed to start: {e}")
            print("Troubleshooting steps:")
            print("1. Ensure all Chrome instances are closed")
            print("2. Check Chrome and ChromeDriver versions")
            print("3. Verify user data directory permissions")
            print("4. Try restarting the system")
            
            # Try fallback options
            print("⏳ Attempting fallback configuration...")
            
            # Fallback: Remove problematic arguments
            fallback_opts = Options()
            fallback_opts.add_experimental_option("prefs", prefs)
            fallback_opts.add_argument("--headless")
            fallback_opts.add_argument("--no-sandbox")
            fallback_opts.add_argument("--disable-dev-shm-usage")
            fallback_opts.add_argument("--disable-gpu")
            fallback_opts.add_argument("--remote-debugging-port=0")
            fallback_opts.add_argument(f"--user-data-dir={PERMANENT_USER_DATA_DIR}")
            fallback_opts.add_argument(f"--profile-directory=Default")
            #profile 2 = pc
            #default = laptop
            
            try:
                fallback_driver = webdriver.Chrome(service=service, options=fallback_opts)
                print("✅ Fallback Chrome driver started successfully")
                return fallback_driver
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {fallback_error}")
                raise Exception(f"Could not start Chrome driver: {e}")
            
    def setup_buying_driver(self):
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.popups": 0,
            "download.prompt_for_download": False,
        }

        service = Service(
                ChromeDriverManager().install(),
                log_path=os.devnull  # Suppress driver logs
            )
        
        fallback_opts = Options()
        fallback_opts.add_experimental_option("prefs", prefs)
        fallback_opts.add_argument("--headless")
        fallback_opts.add_argument("--no-sandbox")
        fallback_opts.add_argument("--disable-dev-shm-usage")
        fallback_opts.add_argument("--disable-gpu")
        fallback_opts.add_argument("--remote-debugging-port=0")
        fallback_opts.add_argument(f"--user-data-dir={VINTED_BUYING_USER_DATA_DIR}")
        fallback_opts.add_argument(f"--profile-directory=Default")
        #Profile 2 = pc
        #Default = laptop
            
        try:
            fallback_driver = webdriver.Chrome(service=service, options=fallback_opts)
            print("✅ Fallback Chrome driver started successfully")
            return fallback_driver
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            raise Exception(f"Could not start Chrome driver")
            
            

    def extract_vinted_price(self, text):
        """
        Enhanced price extraction for Vinted that handles various price formats
        """
        if not text:
            return 0.0
        
        # Remove currency symbols and extra text, extract number
        cleaned_text = re.sub(r'[^\d.,]', '', str(text))
        if not cleaned_text:
            return 0.0
            
        # Handle comma as decimal separator (European format)
        if ',' in cleaned_text and '.' not in cleaned_text:
            cleaned_text = cleaned_text.replace(',', '.')
        elif ',' in cleaned_text and '.' in cleaned_text:
            # Assume comma is thousands separator
            cleaned_text = cleaned_text.replace(',', '')
        
        try:
            return float(cleaned_text)
        except ValueError:
            return 0.0
        
    def detect_console_keywords_vinted(self, listing_title, listing_description):
        """
        Detect console keywords in Vinted title and description (ported from Facebook)
        """
        listing_title_lower = listing_title.lower()
        listing_description_lower = listing_description.lower()
        
        console_keywords = {
            'switch console': 'switch',
            'swith console': 'switch',
            'switc console': 'switch',
            'swich console': 'switch',
            'oled console': 'oled',
            'lite console': 'lite'
        }
        
        # Check if title contains console keywords
        title_contains_console = any(keyword in listing_title_lower for keyword in console_keywords.keys())
        
        # Check if description contains console keywords and title contains relevant terms
        desc_contains_console = any(
            keyword in listing_description_lower and
            any(term in listing_title_lower for term in ['nintendo switch', 'oled', 'lite'])
            for keyword in console_keywords.keys()
        )
        
        detected_console = None
        if title_contains_console or desc_contains_console:
            for keyword, console_type in console_keywords.items():
                if keyword in listing_title_lower or keyword in listing_description_lower:
                    detected_console = console_type
                    break
        
        return detected_console

    def detect_anonymous_games_vinted(self, listing_title, listing_description):
        """
        Detect anonymous games count from title and description (ported from Facebook)
        """
        def extract_games_number(text):
            # Prioritize specific game type matches first
            matches = (
                re.findall(r'(\d+)\s*(switch|nintendo)\s*games', text.lower()) + # Switch/Nintendo specific
                re.findall(r'(\d+)\s*games', text.lower()) # Generic games
            )
            # Convert matches to integers and find the maximum
            numeric_matches = [int(match[0]) if isinstance(match, tuple) else int(match) for match in matches]
            return max(numeric_matches) if numeric_matches else 0
        
        title_games = extract_games_number(listing_title)
        desc_games = extract_games_number(listing_description)
        return max(title_games, desc_games)

    def detect_sd_card_vinted(self, listing_title, listing_description):
        """
        Detect SD card presence in title or description
        """
        sd_card_keywords = {'sd card', 'sdcard', 'sd', 'card', 'memory card', 'memorycard', 'micro sd', 'microsd',
                        'memory card', 'memorycard', 'sandisk', '128gb', '256gb', 'game'}
        
        title_lower = listing_title.lower()
        desc_lower = listing_description.lower()
        
        return any(keyword in title_lower or keyword in desc_lower for keyword in sd_card_keywords)

    def handle_mutually_exclusive_items_vinted(self, detected_objects, confidences):
        """
        Handle mutually exclusive items for Vinted (ported from Facebook)
        """
        mutually_exclusive_items = ['switch', 'oled', 'lite', 'switch_box', 'oled_box', 'lite_box', 'switch_in_tv', 'oled_in_tv']
        
        # Find the item with highest confidence
        selected_item = max(confidences.items(), key=lambda x: x[1])[0] if any(confidences.values()) else None
        
        if selected_item:
            # Set the selected item to 1 and all others to 0
            for item in mutually_exclusive_items:
                detected_objects[item] = 1 if item == selected_item else 0
                
            # Handle accessory incompatibilities
            if selected_item in ['oled', 'oled_in_tv', 'oled_box']:
                detected_objects['tv_black'] = 0
            elif selected_item in ['switch', 'switch_in_tv', 'switch_box']:
                detected_objects['tv_white'] = 0
                
            if selected_item in ['lite', 'lite_box', 'switch_box', 'oled_box']:
                detected_objects['comfort_h'] = 0
                
            if selected_item in ['switch_in_tv', 'switch_box']:
                detected_objects['tv_black'] = 0
                
            if selected_item in ['oled_in_tv', 'oled_box']:
                detected_objects['tv_white'] = 0
        
        return detected_objects

    def handle_oled_title_conversion_vinted(self, detected_objects, listing_title, listing_description):
        """
        Handle OLED title conversion logic (ported from Facebook)
        """
        listing_title_lower = listing_title.lower()
        listing_description_lower = listing_description.lower()
        
        if (('oled' in listing_title_lower) or ('oled' in listing_description_lower)) and \
        'not oled' not in listing_title_lower and 'not oled' not in listing_description_lower:
            
            for old, new in [('switch', 'oled'), ('switch_in_tv', 'oled_in_tv'), ('switch_box', 'oled_box')]:
                if detected_objects.get(old, 0) > 0:
                    detected_objects[old] = 0
                    detected_objects[new] = 1
        
        return detected_objects
    def check_vinted_listing_suitability(self, listing_info):
        """
        Check if a Vinted listing meets all suitability criteria
        """
        title = listing_info.get("title", "").lower()
        description = listing_info.get("description", "").lower()
        price = listing_info.get("price", 0)
        
        try:
            price_float = float(price)
        except (ValueError, TypeError):
            return "Unsuitable: Unable to parse price"
        
        checks = [
            (lambda: any(word in title for word in vinted_title_forbidden_words),
            "Title contains forbidden words"),
            (lambda: not any(word in title for word in vinted_title_must_contain),
            "Title does not contain any required words"),
            (lambda: any(word in description for word in vinted_description_forbidden_words),
            "Description contains forbidden words"),
            (lambda: price_float < vinted_min_price or price_float > vinted_max_price,
            f"Price £{price_float} is outside the range £{vinted_min_price}-£{vinted_max_price}"),
            (lambda: len(re.findall(r'[£$]\s*\d+|\d+\s*[£$]', description)) >= 3,
            "Too many $ symbols in description"),
            (lambda: price_float in vinted_banned_prices,
            "Price in banned prices list")
        ]
        
        for check, message in checks:
            try:
                if check():
                    return f"Unsuitable: {message}"
            except (ValueError, IndexError, AttributeError, TypeError):
                continue
        
        return "Listing is suitable"

    def scrape_item_details(self, driver):
        """
        Enhanced scraper with better price extraction and seller reviews
        """
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "p.web_ui__Text__subtitle"))
        )

        fields = {
            "title": "h1.web_ui__Text__title",
            "price": "p.web_ui__Text__subtitle",  # Main price field for extraction
            "second_price": "div.web_ui__Text__title.web_ui__Text__clickable.web_ui__Text__underline-none",
            "postage": "h3[data-testid='item-shipping-banner-price']",
            "description": "span.web_ui__Text__text.web_ui__Text__body.web_ui__Text__left.web_ui__Text__format span",
            "uploaded": "span.web_ui__Text__text.web_ui__Text__subtitle.web_ui__Text__left.web_ui__Text__bold",
            "seller_reviews": "span.web_ui__Text__text.web_ui__Text__caption.web_ui__Text__left",  # New field for seller reviews
        }

        data = {}
        for key, sel in fields.items():
            try:
                if key == "seller_reviews":
                    # Special handling for seller reviews - get the text content
                    element = driver.find_element(By.CSS_SELECTOR, sel)
                    text = element.text.strip()
                    
                    # Check if it's the "No reviews yet" case or a number
                    if text == "No reviews yet":
                        data[key] = "No reviews yet"
                    else:
                        # Extract just the number if it's numeric
                        if text.isdigit():
                            data[key] = f"Reviews: {text}"
                        else:
                            data[key] = "No reviews yet"
                else:
                    data[key] = driver.find_element(By.CSS_SELECTOR, sel).text
            except NoSuchElementException:
                if key == "seller_reviews":
                    data[key] = "No reviews yet"
                else:
                    data[key] = None

        # Keep title formatting for pygame display
        if data["title"]:
            data["title"] = data["title"][:50] + '...' if len(data["title"]) > 50 else data["title"]

        return data

    def clear_download_folder(self):
        if os.path.exists(DOWNLOAD_ROOT):
            shutil.rmtree(DOWNLOAD_ROOT)
        os.makedirs(DOWNLOAD_ROOT, exist_ok=True)

    def process_vinted_listing(self, details, detected_objects, processed_images, listing_counter, url):
        """
        Enhanced processing with comprehensive filtering and analysis - FIXED for navigation
        """
        global suitable_listings, current_listing_index, recent_listings

        # Extract and validate price from the main price field
        price_text = details.get("price", "0")
        listing_price = self.extract_vinted_price(price_text)
        postage = self.extract_price(details.get("postage", "0"))
        total_price = listing_price + postage

        # Get seller reviews
        seller_reviews = details.get("seller_reviews", "No reviews yet")

        # Create basic listing info for suitability checking
        listing_info = {
            "title": details.get("title", "").lower(),
            "description": details.get("description", "").lower(),
            "price": total_price,
            "url": url
        }

        # Check basic suitability (but don't exit early if VINTED_SHOW_ALL_LISTINGS is True)
        suitability_result = self.check_vinted_listing_suitability(listing_info)

        # Apply console keyword detection to detected objects
        detected_console = self.detect_console_keywords_vinted(
            details.get("title", ""),
            details.get("description", "")
        )
        if detected_console:
            # Set the detected console to 1 and ensure other mutually exclusive items are 0
            mutually_exclusive_items = ['switch', 'oled', 'lite', 'switch_box', 'oled_box', 'lite_box', 'switch_in_tv', 'oled_in_tv']
            for item in mutually_exclusive_items:
                detected_objects[item] = 1 if item == detected_console else 0

        # Apply OLED title conversion
        detected_objects = self.handle_oled_title_conversion_vinted(
            detected_objects,
            details.get("title", ""),
            details.get("description", "")
        )

        # Calculate revenue with enhanced logic
        total_revenue, expected_profit, profit_percentage, display_objects = self.calculate_vinted_revenue(
            detected_objects, total_price, details.get("title", ""), details.get("description", "")
        )

        # Check profit suitability
        profit_suitability = self.check_vinted_profit_suitability(total_price, profit_percentage)

        # Game count suitability check (same as Facebook) - but don't return early if showing all
        game_classes = [
            '1_2_switch', 'animal_crossing', 'arceus_p', 'bow_z', 'bros_deluxe_m', 'crash_sand',
            'dance', 'diamond_p', 'evee', 'fifa_23', 'fifa_24', 'gta','just_dance', 'kart_m', 'kirby',
            'lets_go_p', 'links_z', 'luigis', 'mario_maker_2', 'mario_sonic', 'mario_tennis', 'minecraft',
            'minecraft_dungeons', 'minecraft_story', 'miscellanious_sonic', 'odyssey_m', 'other_mario',
            'party_m', 'rocket_league', 'scarlet_p', 'shield_p', 'shining_p', 'skywards_z', 'smash_bros',
            'snap_p', 'splatoon_2', 'splatoon_3', 'super_m_party', 'super_mario_3d', 'switch_sports',
            'sword_p', 'tears_z', 'violet_p'
        ]
        game_count = sum(detected_objects.get(game, 0) for game in game_classes)
        non_game_classes = [cls for cls in detected_objects.keys() if cls not in game_classes and detected_objects.get(cls, 0) > 0]

        # Build comprehensive suitability reason
        unsuitability_reasons = []

        # Add basic suitability issues
        if "Unsuitable" in suitability_result:
            unsuitability_reasons.append(suitability_result.replace("Unsuitable: ", ""))

        # Add game count issue
        if 1 <= game_count <= 2 and not non_game_classes:
            unsuitability_reasons.append("1-2 games with no additional non-game items")

        # Add profit suitability issue
        if not profit_suitability:
            unsuitability_reasons.append(f"Profit £{expected_profit:.2f} ({profit_percentage:.2f}%) not suitable for price range")

        # Determine final suitability
        if unsuitability_reasons:
            suitability_reason = "Unsuitable:\n---- " + "\n---- ".join(unsuitability_reasons)
            is_suitable = False
        else:
            suitability_reason = f"Suitable: Profit £{expected_profit:.2f} ({profit_percentage:.2f}%)"
            is_suitable = True

        # Create final listing info
        final_listing_info = {
            'title': details.get("title", "No title"),
            'description': details.get("description", "No description"),
            'join_date': details.get("uploaded", "Unknown upload date"),
            'price': str(total_price),
            'expected_revenue': total_revenue,
            'profit': expected_profit,
            'detected_items': detected_objects, # Raw detected objects for box 1
            'processed_images': processed_images,
            'bounding_boxes': {'image_paths': [], 'detected_objects': detected_objects},
            'url': url,
            'suitability': suitability_reason,
            'seller_reviews': seller_reviews  # NEW: Add seller reviews to listing info
        }

        # Add to suitable listings based on VINTED_SHOW_ALL_LISTINGS setting
        if is_suitable or VINTED_SHOW_ALL_LISTINGS:
            # **NEW: Send Pushover notification (same logic as Facebook)**
            notification_title = f"New Vinted Listing: £{total_price:.2f}"
            notification_message = (
                f"Title: {details.get('title', 'No title')}\n"
                f"Price: £{total_price:.2f}\n"
                f"Expected Profit: £{expected_profit:.2f}\n"
                f"Profit %: {profit_percentage:.2f}%\n"
            )
            
            # Use the Pushover tokens exactly as Facebook does
            if send_notification:
                self.send_pushover_notification(
                    notification_title,
                    notification_message,
                    'aks3to8guqjye193w7ajnydk9jaxh5',
                    'ucwc6fi1mzd3gq2ym7jiwg3ggzv1pc'
                )

            suitable_listings.append(final_listing_info)

            # **CRITICAL FIX: Add to recent_listings for website navigation**
            recent_listings['listings'].append(final_listing_info)
            # Always set to the last (most recent) listing for website display
            recent_listings['current_index'] = len(recent_listings['listings']) - 1

            current_listing_index = len(suitable_listings) - 1
            self.update_listing_details(**final_listing_info)

            if is_suitable:
                print(f"✅ Added suitable listing: £{total_price:.2f} -> £{expected_profit:.2f} profit ({profit_percentage:.2f}%)")
            else:
                print(f"➕ Added unsuitable listing (SHOW_ALL mode): £{total_price:.2f}")
        else:
            print(f"❌ Listing not added: {suitability_reason}")

    def check_vinted_profit_suitability(self, listing_price, profit_percentage):
        if 10 <= listing_price < 16:
            return 100 <= profit_percentage <= 600 #50
        elif 16 <= listing_price < 25:
            return 65 <= profit_percentage <= 400 #50
        elif 25 <= listing_price < 50:
            return 37.5 <= profit_percentage <= 550 #35
        elif 50 <= listing_price < 100:
            return 35 <= profit_percentage <= 500 #32.5
        elif listing_price >= 100:
            return 30 <= profit_percentage <= 450 # 30
        else:
            return False
            
    def calculate_vinted_revenue(self, detected_objects, listing_price, title, description=""):
        """
        Enhanced revenue calculation with all Facebook logic
        """
        # List of game-related classes
        game_classes = [
            '1_2_switch', 'animal_crossing', 'arceus_p', 'bow_z', 'bros_deluxe_m', 'crash_sand',
            'dance', 'diamond_p', 'evee', 'fifa_23', 'fifa_24', 'gta','just_dance', 'kart_m', 'kirby',
            'lets_go_p', 'links_z', 'luigis', 'mario_maker_2', 'mario_sonic', 'mario_tennis', 'minecraft',
            'minecraft_dungeons', 'minecraft_story', 'miscellanious_sonic', 'odyssey_m', 'other_mario',
            'party_m', 'rocket_league', 'scarlet_p', 'shield_p', 'shining_p', 'skywards_z', 'smash_bros',
            'snap_p', 'splatoon_2', 'splatoon_3', 'super_m_party', 'super_mario_3d', 'switch_sports',
            'sword_p', 'tears_z', 'violet_p'
        ]

        # Get all prices
        all_prices = self.fetch_all_prices()

        # Count detected games
        detected_games_count = sum(detected_objects.get(game, 0) for game in game_classes)

        # Detect anonymous games from title and description
        text_games_count = self.detect_anonymous_games_vinted(title, description)

        # Calculate miscellaneous games
        misc_games_count = max(0, text_games_count - detected_games_count)
        misc_games_revenue = misc_games_count * 5 # Using same price as Facebook

        # Handle box adjustments (same as Facebook)
        adjustments = {
            'oled_box': ['switch', 'comfort_h', 'tv_white'],
            'switch_box': ['switch', 'comfort_h', 'tv_black'],
            'lite_box': ['lite']
        }

        for box, items in adjustments.items():
            box_count = detected_objects.get(box, 0)
            for item in items:
                detected_objects[item] = max(0, detected_objects.get(item, 0) - box_count)

        # Remove switch_screen if present
        detected_objects.pop('switch_screen', None)

        # Detect SD card and add revenue
        total_revenue = misc_games_revenue
        if self.detect_sd_card_vinted(title, description):
            total_revenue += 5 # Same SD card revenue as Facebook
            print(f"SD Card detected: Added £5 to revenue")

        # Calculate revenue from detected objects
        for item, count in detected_objects.items():
            if isinstance(count, str):
                count_match = re.match(r'(\d+)', count)
                count = int(count_match.group(1)) if count_match else 0

            if count > 0 and item in all_prices:
                item_price = all_prices[item]
                if item == 'controller' and 'pro' in title.lower():
                    item_price += 7.50
                
                item_revenue = item_price * count
                total_revenue += item_revenue

        expected_profit = total_revenue - listing_price
        profit_percentage = (expected_profit / listing_price) * 100 if listing_price > 0 else 0

        print(f"\nVinted Revenue Breakdown:")
        print(f"Listing Price: £{listing_price:.2f}")
        print(f"Total Expected Revenue: £{total_revenue:.2f}")
        print(f"Expected Profit/Loss: £{expected_profit:.2f} ({profit_percentage:.2f}%)")

        # CRITICAL FIX: Filter out zero-count items for display (matching Facebook behavior)
        display_objects = {k: v for k, v in detected_objects.items() if v > 0}

        # Add miscellaneous games to display if present
        if misc_games_count > 0:
            display_objects['misc_games'] = misc_games_count

        return total_revenue, expected_profit, profit_percentage, display_objects

    def perform_detection_on_listing_images(self, model, listing_dir):
        """
        Enhanced object detection with all Facebook exceptions and logic
        PLUS Vinted-specific post-scan game deduplication
        """
        if not os.path.isdir(listing_dir):
            return {}, []

        detected_objects = {class_name: [] for class_name in CLASS_NAMES}
        processed_images = []
        confidences = {item: 0 for item in ['switch', 'oled', 'lite', 'switch_box', 'oled_box', 'lite_box', 'switch_in_tv', 'oled_in_tv']}

        image_files = [f for f in os.listdir(listing_dir) if f.endswith('.png')]
        if not image_files:
            return {class_name: 0 for class_name in CLASS_NAMES}, processed_images

        for image_file in image_files:
            image_path = os.path.join(listing_dir, image_file)
            try:
                img = cv2.imread(image_path)
                if img is None:
                    continue

                # Track detections for this image
                image_detections = {class_name: 0 for class_name in CLASS_NAMES}
                results = model(img, verbose=False)
                
                for result in results:
                    for box in result.boxes.cpu().numpy():
                        class_id = int(box.cls[0])
                        confidence = box.conf[0]
                        
                        if class_id < len(CLASS_NAMES):
                            class_name = CLASS_NAMES[class_id]
                            min_confidence = HIGHER_CONFIDENCE_ITEMS.get(class_name, GENERAL_CONFIDENCE_MIN)
                            
                            if confidence >= min_confidence:
                                if class_name in ['switch', 'oled', 'lite', 'switch_box', 'oled_box', 'lite_box', 'switch_in_tv', 'oled_in_tv']:
                                    confidences[class_name] = max(confidences[class_name], confidence)
                                else:
                                    image_detections[class_name] += 1
                                
                                # Draw bounding box
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(img, f"{class_name} ({confidence:.2f})", (x1, y1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.625, (0, 255, 0), 2)

                # Update overall detected objects with max from this image
                for class_name, count in image_detections.items():
                    detected_objects[class_name].append(count)

                # Convert to PIL Image for pygame compatibility
                processed_images.append(Image.fromarray(cv2.cvtColor(
                    cv2.copyMakeBorder(img, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=[0, 0, 0]),
                    cv2.COLOR_BGR2RGB)))

            except Exception as e:
                print(f"Error processing image {image_path}: {str(e)}")
                continue

        # Convert lists to max values
        final_detected_objects = {class_name: max(counts) if counts else 0 for class_name, counts in detected_objects.items()}
        
        # Handle mutually exclusive items
        final_detected_objects = self.handle_mutually_exclusive_items_vinted(final_detected_objects, confidences)
        
        # VINTED-SPECIFIC POST-SCAN GAME DEDUPLICATION
        # Define game classes that should be capped at 1 per listing
        vinted_game_classes = [
            '1_2_switch', 'animal_crossing', 'arceus_p', 'bow_z', 'bros_deluxe_m', 'crash_sand',
            'dance', 'diamond_p', 'evee', 'fifa_23', 'fifa_24', 'gta', 'just_dance', 'kart_m', 'kirby',
            'lets_go_p', 'links_z', 'luigis', 'mario_maker_2', 'mario_sonic', 'mario_tennis', 'minecraft',
            'minecraft_dungeons', 'minecraft_story', 'miscellanious_sonic', 'odyssey_m', 'other_mario',
            'party_m', 'rocket_league', 'scarlet_p', 'shield_p', 'shining_p', 'skywards_z', 'smash_bros',
            'snap_p', 'splatoon_2', 'splatoon_3', 'super_m_party', 'super_mario_3d', 'switch_sports',
            'sword_p', 'tears_z', 'violet_p'
        ]
        
        # Cap each game type to maximum 1 per listing for Vinted
        games_before_cap = {}
        for game_class in vinted_game_classes:
            if final_detected_objects.get(game_class, 0) > 1:
                games_before_cap[game_class] = final_detected_objects[game_class]
                final_detected_objects[game_class] = 1
        
        # Log the capping if any games were capped
        if games_before_cap:
            print("🎮 VINTED GAME DEDUPLICATION APPLIED:")
            for game, original_count in games_before_cap.items():
                print(f"  • {game}: {original_count} → 1")
        
        return final_detected_objects, processed_images

        
    def download_images_for_listing(self, driver, listing_dir):
        # Wait for the page to fully load
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "img"))
            )
            # Additional wait for dynamic content
        except TimeoutException:
            print("  ▶ Timeout waiting for images to load")
            return []
        
        # Try multiple selectors in order of preference - focusing on product images only
        img_selectors = [
            # Target product images specifically (avoid profile pictures)
            "img.web_ui__Image__content[data-testid^='item-photo-']",
            "img[data-testid^='item-photo-']",
            # Target images within containers that suggest product photos
            "div.web_ui__Image__cover img.web_ui__Image__content",
            "div.web_ui__Image__scaled img.web_ui__Image__content",
            "div.web_ui__Image__rounded img.web_ui__Image__content",
            # Broader selectors but still avoiding profile images
            "div.feed-grid img",
            "div[class*='photo'] img",
        ]
        
        imgs = []
        for selector in img_selectors:
            imgs = driver.find_elements(By.CSS_SELECTOR, selector)
            if imgs:
                print(f"  ▶ Found {len(imgs)} images using selector: {selector}")
                break
        
        if not imgs:
            print("  ▶ No images found with any selector")
            return []
        
        # Filter images more strictly to avoid profile pictures and small icons
        valid_imgs = []
        for img in imgs:
            src = img.get_attribute("src")
            parent_classes = ""
            
            # Get parent element classes to check for profile picture indicators
            try:
                parent = img.find_element(By.XPATH, "..")
                parent_classes = parent.get_attribute("class") or ""
            except:
                pass
            
            # Check if this is a valid product image
            if src and src.startswith('http'):
                # Exclude profile pictures and small icons based on URL patterns
                if (
                    # Skip small profile pictures (50x50, 75x75, etc.)
                    '/50x50/' in src or 
                    '/75x75/' in src or 
                    '/100x100/' in src or
                    # Skip if parent has circle class (usually profile pics)
                    'circle' in parent_classes.lower() or
                    # Skip SVG icons
                    src.endswith('.svg') or
                    # Skip very obviously small images by checking dimensions in URL
                    any(size in src for size in ['/32x32/', '/64x64/', '/128x128/'])
                ):
                    continue
                
                # Only include images that look like product photos
                if (
                    # Vinted product images typically have f800, f1200, etc.
                    '/f800/' in src or 
                    '/f1200/' in src or 
                    '/f600/' in src or
                    # Or contain vinted/cloudinary and are likely product images
                    (('vinted' in src.lower() or 'cloudinary' in src.lower() or 'amazonaws' in src.lower()) and
                    # And don't have small size indicators
                    not any(small_size in src for small_size in ['/50x', '/75x', '/100x', '/thumb']))
                ):
                    valid_imgs.append(img)
        
        if not valid_imgs:
            print(f"  ▶ No valid product images found after filtering from {len(imgs)} total images")
            # Debug: print what we found for troubleshooting
            for i, img in enumerate(imgs[:5]):  # Show first 5 for debugging
                src = img.get_attribute("src")
                alt = img.get_attribute("alt")
                try:
                    parent = img.find_element(By.XPATH, "..")
                    parent_classes = parent.get_attribute("class") or ""
                except:
                    parent_classes = "unknown"
                print(f"    Image {i+1}: src='{src[:80]}...', alt='{alt}', parent_classes='{parent_classes}'")
            return []

        os.makedirs(listing_dir, exist_ok=True)
        downloaded_paths = []
        seen_urls = set()
        image_index = 1

        print(f"  ▶ Attempting to download {len(valid_imgs)} product images")
        
        for img_el in valid_imgs[:10]:  # Limit to first 10 images
            src = img_el.get_attribute("src")
            if not src or src in seen_urls:
                continue

            seen_urls.add(src)

            try:
                # Add headers to mimic browser request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Referer': driver.current_url
                }
                
                resp = requests.get(src, timeout=15, headers=headers)
                resp.raise_for_status()
                
                # Verify it's actually an image
                img = Image.open(BytesIO(resp.content))
                
                # Skip very small images (likely icons or profile pics that got through)
                if img.width < 200 or img.height < 200:
                    print(f"    ⏭️  Skipping small image: {img.width}x{img.height}")
                    continue
                
                save_path = os.path.join(listing_dir, f"{image_index}.png")
                img.save(save_path, format="PNG")
                downloaded_paths.append(save_path)
                image_index += 1
                print(f"    ✅ Downloaded product image {image_index-1}: {img.width}x{img.height}")

            except Exception as e:
                print(f"    ❌ Failed to download image from {src[:50]}...: {str(e)}")
                continue

        print(f"  ▶ Successfully downloaded {len(downloaded_paths)} product images")
        return downloaded_paths

    
    def extract_vinted_listing_id(self, url):
        """
        Extract listing ID from Vinted URL
        Example: https://www.vinted.co.uk/items/6862154542-sonic-forces?referrer=catalog
        Returns: "6862154542"
        """
        if not url:
            return None
        
        # Match pattern: /items/[numbers]-
        match = re.search(r'/items/(\d+)-', url)
        if match:
            return match.group(1)
        
        # Fallback: match any sequence of digits after /items/
        match = re.search(r'/items/(\d+)', url)
        if match:
            return match.group(1)
        
        return None

    def load_scanned_vinted_ids(self):
        """Load previously scanned Vinted listing IDs from file"""
        try:
            if os.path.exists(VINTED_SCANNED_IDS_FILE):
                with open(VINTED_SCANNED_IDS_FILE, 'r') as f:
                    return set(line.strip() for line in f if line.strip())
            return set()
        except Exception as e:
            print(f"Error loading scanned IDs: {e}")
            return set()

    def save_vinted_listing_id(self, listing_id):
        """Save a Vinted listing ID to the scanned file"""
        if not listing_id:
            return
        
        try:
            with open(VINTED_SCANNED_IDS_FILE, 'a') as f:
                f.write(f"{listing_id}\n")
        except Exception as e:
            print(f"Error saving listing ID {listing_id}: {e}")

    def is_vinted_listing_already_scanned(self, url, scanned_ids):
        """Check if a Vinted listing has already been scanned"""
        listing_id = self.extract_vinted_listing_id(url)
        if not listing_id:
            return False
        return listing_id in scanned_ids

    def refresh_vinted_page_and_wait(self, driver, is_first_refresh=True):
        """
        Refresh the Vinted page and wait appropriate time
        """
        print("🔄 Refreshing Vinted page...")
        
        # Navigate back to first page
        params = {
            "search_text": SEARCH_QUERY,
            "price_from": PRICE_FROM,
            "price_to": PRICE_TO,
            "currency": CURRENCY,
            "order": ORDER,
        }
        driver.get(f"{BASE_URL}?{urlencode(params)}")
        
        # Wait for page to load
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.feed-grid"))
            )
            print("✅ Page refreshed and loaded successfully")
        except TimeoutException:
            print("⚠️ Timeout waiting for page to reload")
        
        # Wait for new listings (except first refresh)
        if not is_first_refresh:
            print(f"⏳ Waiting {wait_after_max_reached_vinted} seconds for new listings...")
            time.sleep(wait_after_max_reached_vinted)
        
        return True

    def search_vinted_with_refresh(self, driver, search_query):
        """
        Enhanced search_vinted method with refresh and rescan functionality
        """
        global suitable_listings, current_listing_index
        
        # CLEAR THE VINTED SCANNED IDS FILE AT THE BEGINNING OF EACH RUN
        try:
            with open(VINTED_SCANNED_IDS_FILE, 'w') as f:
                pass  # This creates an empty file, clearing any existing content
            print(f"✅ Cleared {VINTED_SCANNED_IDS_FILE} at the start of the run")
        except Exception as e:
            print(f"⚠️ Warning: Could not clear {VINTED_SCANNED_IDS_FILE}: {e}")
        
        # Clear previous results
        suitable_listings.clear()
        current_listing_index = 0
        
        # Ensure root download folder exists
        os.makedirs(DOWNLOAD_ROOT, exist_ok=True)

        # Load YOLO Model Once
        print("🧠 Loading object detection model...")
        model = None
        if not os.path.exists(MODEL_WEIGHTS):
            print(f"❌ Critical Error: Model weights not found at '{MODEL_WEIGHTS}'. Detection will be skipped.")
        else:
            try:
                model = YOLO(MODEL_WEIGHTS)
                print("✅ Model loaded successfully.")
            except Exception as e:
                print(f"❌ Critical Error: Could not load YOLO model. Detection will be skipped. Reason: {e}")

        # Initial page setup
        params = {
            "search_text": search_query,
            "price_from": PRICE_FROM,
            "price_to": PRICE_TO,
            "currency": CURRENCY,
            "order": ORDER,
        }
        driver.get(f"{BASE_URL}?{urlencode(params)}")
        main = driver.current_window_handle

        # Load previously scanned listing IDs (this will now be empty since we cleared the file)
        scanned_ids = self.load_scanned_vinted_ids()
        print(f"📚 Loaded {len(scanned_ids)} previously scanned listing IDs")

        page = 1
        overall_listing_counter = 0  # Total listings processed across all cycles
        refresh_cycle = 1
        is_first_refresh = True

        # Main scanning loop with refresh functionality
        while True:
            print(f"\n{'='*60}")
            print(f"🔍 STARTING REFRESH CYCLE {refresh_cycle}")
            print(f"{'='*60}")
            
            cycle_listing_counter = 0  # Listings processed in this cycle
            found_already_scanned = False
            
            # Reset to first page for each cycle
            page = 1
            
            while True:  # Page loop
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.feed-grid"))
                    )
                except TimeoutException:
                    print("⚠️ Timeout waiting for page to load - moving to next cycle")
                    break

                # Get listing URLs from current page
                els = driver.find_elements(By.CSS_SELECTOR, "a.new-item-box__overlay")
                urls = [e.get_attribute("href") for e in els if e.get_attribute("href")]
                
                if not urls:
                    print(f"📄 No listings found on page {page} - moving to next cycle")
                    break

                print(f"📄 Processing page {page} with {len(urls)} listings")

                for idx, url in enumerate(urls, start=1):
                    overall_listing_counter += 1
                    cycle_listing_counter += 1
                    
                    print(f"[Cycle {refresh_cycle} · Page {page} · Item {idx}/{len(urls)}] #{overall_listing_counter}")
                    
                    # Extract listing ID and check if already scanned
                    listing_id = self.extract_vinted_listing_id(url)
                    
                    if REFRESH_AND_RESCAN and listing_id:
                        if listing_id in scanned_ids:
                            print(f"🔁 DUPLICATE DETECTED: Listing ID {listing_id} already scanned")
                            print(f"🔄 Initiating refresh and rescan process...")
                            found_already_scanned = True
                            break
                    
                    # Check if we've hit the maximum listings for this cycle
                    if REFRESH_AND_RESCAN and cycle_listing_counter > MAX_LISTINGS_VINTED_TO_SCAN:
                        print(f"📊 Reached MAX_LISTINGS_VINTED_TO_SCAN ({MAX_LISTINGS_VINTED_TO_SCAN})")
                        print(f"🔄 Initiating refresh cycle...")
                        break

                    # Process the listing (same as original logic)
                    driver.execute_script("window.open();")
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.get(url)

                    try:
                        details = self.scrape_item_details(driver)
                        second_price = self.extract_price(details["second_price"])
                        postage = self.extract_price(details["postage"])
                        total_price = second_price + postage

                        print(f"  Link:         {url}")
                        print(f"  Title:        {details['title']}")
                        print(f"  Price:        {details['price']}")
                        print(f"  Second price: {details['second_price']} ({second_price:.2f})")
                        print(f"  Postage:      {details['postage']} ({postage:.2f})")
                        print(f"  Total price:  £{total_price:.2f}")
                        print(f"  Uploaded:     {details['uploaded']}")

                        # Download images for the current listing
                        listing_dir = os.path.join(DOWNLOAD_ROOT, f"listing {overall_listing_counter}")
                        image_paths = self.download_images_for_listing(driver, listing_dir)

                        # Perform object detection and get processed images
                        detected_objects = {}
                        processed_images = []
                        if model and image_paths:
                            detected_objects, processed_images = self.perform_detection_on_listing_images(model, listing_dir)
                            
                            # Print detected objects
                            detected_classes = [cls for cls, count in detected_objects.items() if count > 0]
                            if detected_classes:
                                for cls in sorted(detected_classes):
                                    print(f"  • {cls}: {detected_objects[cls]}")

                        # Process listing for pygame display
                        self.process_vinted_listing(details, detected_objects, processed_images, overall_listing_counter, url)

                        # Mark this listing as scanned
                        if listing_id:
                            scanned_ids.add(listing_id)
                            self.save_vinted_listing_id(listing_id)
                            print(f"✅ Saved listing ID: {listing_id}")

                        print("-" * 40)

                    except Exception as e:
                        print(f"  ❌ ERROR scraping listing: {e}")
                        # Still mark as scanned even if there was an error
                        if listing_id:
                            scanned_ids.add(listing_id)
                            self.save_vinted_listing_id(listing_id)

                    finally:
                        driver.close()
                        driver.switch_to.window(main)

                # Check if we need to break out of page loop
                if found_already_scanned or (REFRESH_AND_RESCAN and cycle_listing_counter > MAX_LISTINGS_VINTED_TO_SCAN):
                    break

                # Try to go to next page
                try:
                    nxt = driver.find_element(By.CSS_SELECTOR, "a[data-testid='pagination-arrow-right']")
                    driver.execute_script("arguments[0].click();", nxt)
                    page += 1
                    time.sleep(2)
                except NoSuchElementException:
                    print("📄 No more pages available - moving to next cycle")
                    break

            # End of page loop - decide whether to continue or refresh
            if not REFRESH_AND_RESCAN:
                print("🏁 REFRESH_AND_RESCAN disabled - ending scan")
                break
            
            if found_already_scanned:
                print(f"🔁 Found already scanned listing - refreshing immediately")
                self.refresh_vinted_page_and_wait(driver, is_first_refresh)
            elif cycle_listing_counter > MAX_LISTINGS_VINTED_TO_SCAN:
                print(f"📊 Reached maximum listings ({MAX_LISTINGS_VINTED_TO_SCAN}) - refreshing")
                self.refresh_vinted_page_and_wait(driver, is_first_refresh)
            else:
                print("📄 No more pages and no max reached - refreshing for new listings")
                self.refresh_vinted_page_and_wait(driver, is_first_refresh)

            refresh_cycle += 1
            is_first_refresh = False

    def start_cloudflare_tunnel(self, port=5000):
        """
        Starts a Cloudflare Tunnel using the cloudflared binary.
        Adjust the cloudflared_path if your executable is in a different location.
        """
        # Path to the cloudflared executable
        #pc
        #cloudflared_path = r"C:\Users\ZacKnowsHow\Downloads\cloudflared.exe"
        #laptop
        cloudflared_path = r"C:\Users\zacha\Downloads\cloudflared.exe"
        
        # Start the tunnel with the desired command-line arguments
        process = subprocess.Popen(
            [cloudflared_path, "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Function to read and print cloudflared output asynchronously
        def read_output(proc):
            for line in proc.stdout:
                print("[cloudflared]", line.strip())
        
        # Start a thread to print cloudflared output so you can see the public URL and any errors
        threading.Thread(target=read_output, args=(process,), daemon=True).start()
        
        # Wait a few seconds for the tunnel to establish (adjust if needed).
        time.sleep(5)
        return process

    def run_flask_app(self):
        try:
            print("Starting Flask app for https://fk43b0p45crc03r.xyz/")
            
            # Run Flask locally - your domain should be configured to tunnel to this
            app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
            
        except Exception as e:
            print(f"Error starting Flask app: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        global suitable_listings, current_listing_index, recent_listings, current_listing_title, current_listing_price
        global current_listing_description, current_listing_join_date, current_detected_items, current_profit
        global current_listing_images, current_listing_url, current_suitability, current_expected_revenue
        
        # Initialize ALL global variables properly
        suitable_listings = []
        current_listing_index = 0
        
