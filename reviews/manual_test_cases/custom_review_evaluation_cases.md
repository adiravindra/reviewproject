# Manual Review Evaluation Cases

These examples are for manual evaluation only. They are designed to check whether ReviewInsight produces detailed summaries and highlights complete sentiment words and multi-word phrases.

## 1. Positive: Service Value And Flexibility

**Review text:** Rudy with RM Junk Removal gave us the best service during a stressful move. The price was better than every other quote we received, his communication was excellent, and he arrived exactly at the scheduled time for both drop-off and pickup. When our closing date changed, Rudy adjusted the day without making us feel like a burden. He was professional from start to finish, and this was absolutely 5-star service.

**Expected sentiment:** positive

**Expected sentiment keywords/phrases:** best service; better than every other quote; communication was excellent; exactly at the scheduled time; adjusted the day; professional; 5-star service

**Expected summary:** The customer strongly praises Rudy and RM Junk Removal for competitive pricing, excellent communication, punctual drop-off and pickup, flexibility during a stressful move, and professional service. The review describes a dependable experience where the business adapted to the customer's changing schedule. Overall, the customer views the service as a clear 5-star experience.

**Notes:** This case should highlight several multi-word positive phrases instead of only single words like "best" or "excellent."

## 2. Positive: Product Quality And Support Follow-Through

**Review text:** I ordered this coffee grinder after comparing several options, and it exceeded expectations. The build quality feels sturdy, the grind is consistent, and the customer support team answered my setup question within an hour. I especially appreciated that the replacement part arrived before the weekend, which kept my routine from being interrupted. I would recommend this product without hesitation.

**Expected sentiment:** positive

**Expected sentiment keywords/phrases:** exceeded expectations; build quality feels sturdy; grind is consistent; answered my setup question within an hour; replacement part arrived before the weekend; would recommend

**Expected summary:** The customer is very satisfied with the coffee grinder's sturdy build, consistent performance, and fast customer support. The review also praises the company for sending a replacement part quickly enough to avoid disrupting the customer's routine. Overall, the customer recommends the product with confidence.

**Notes:** The sentiment depends on longer praise phrases about quality, consistency, and support responsiveness.

## 3. Negative: Delivery Failure And Poor Communication

**Review text:** The couch looked nice online, but the delivery experience was terrible. The carrier missed the scheduled window twice, nobody called with an update, and the support chat kept telling me to wait another day. When it finally arrived, one leg was cracked and the fabric had a stain. I asked for a refund because the whole process felt careless.

**Expected sentiment:** negative

**Expected sentiment keywords/phrases:** delivery experience was terrible; missed the scheduled window twice; nobody called with an update; kept telling me to wait another day; one leg was cracked; fabric had a stain; asked for a refund; felt careless

**Expected summary:** The customer is unhappy with both the delivery process and the damaged couch. They report missed delivery windows, poor communication, unhelpful support, and product damage on arrival. Overall, the review signals a negative experience driven by reliability, communication, and quality failures.

**Notes:** The app should not over-focus on "looked nice online"; the later delivery and damage details control the sentiment.

## 4. Negative: Restaurant Timing And Food Quality

**Review text:** We wanted to like this restaurant because the staff was friendly, but dinner took almost two hours and most of the food arrived cold. The server apologized, yet no one explained why the kitchen was so backed up. The steak was overcooked, the fries were soggy, and the manager only offered a small discount after we asked. It was not worth the price.

**Expected sentiment:** negative

**Expected sentiment keywords/phrases:** dinner took almost two hours; food arrived cold; no one explained; steak was overcooked; fries were soggy; small discount after we asked; not worth the price

**Expected summary:** The customer describes a disappointing restaurant visit despite friendly staff. Long wait times, cold food, poor explanation from the kitchen, overcooked steak, soggy fries, and weak compensation shaped the negative experience. Overall, the customer felt the meal did not justify the price.

**Notes:** This is a mixed-signal review, but the dominant sentiment should be negative because the operational and food-quality issues outweigh the friendly staff.

## 5. Neutral: Functional But Unremarkable Product

**Review text:** The backpack is fine for everyday errands. It holds my laptop, the zippers work, and the color matches the listing. The straps are not especially comfortable on longer walks, but nothing has broken so far. I would not call it amazing, but it does what I expected for the price.

**Expected sentiment:** neutral

**Expected sentiment keywords/phrases:** fine for everyday errands; zippers work; matches the listing; not especially comfortable; nothing has broken; does what I expected for the price

**Expected summary:** The customer sees the backpack as acceptable and functional rather than impressive. They mention useful basics such as laptop storage, working zippers, accurate color, and no breakage, while also noting that the straps are uncomfortable for longer walks. Overall, the review is neutral because the product meets expectations without creating strong satisfaction.

**Notes:** The phrase "not amazing" should not be treated as strongly negative; the full context is neutral.

## 6. Mixed: Great Cleaner, Weak Bottle Design

**Review text:** The cleaning spray works very well on grease, and the scent is much better than the harsh products I used before. However, the bottle leaks if it tips over, and the trigger stuck after a week. I like the actual cleaner, but the packaging makes it frustrating to use every day.

**Expected sentiment:** neutral

**Expected sentiment keywords/phrases:** works very well on grease; scent is much better; bottle leaks; trigger stuck after a week; frustrating to use every day

**Expected summary:** The customer likes the cleaning product itself because it handles grease well and has a better scent than harsher alternatives. However, leaking packaging and a trigger that stuck after one week make the daily experience frustrating. Overall, the review is mixed because product performance is positive but usability is negative.

**Notes:** The summary should preserve both sides. Highlighting should include both positive and negative phrases if the UI is not filtering by one sentiment.

## 7. Positive: Healthcare Scheduling And Bedside Manner

**Review text:** The clinic made a nervous appointment feel much easier. The front desk explained the forms clearly, the nurse listened without rushing me, and the doctor walked through the test results in plain language. I left feeling informed and respected. That kind of communication makes a huge difference.

**Expected sentiment:** positive

**Expected sentiment keywords/phrases:** feel much easier; explained the forms clearly; listened without rushing me; plain language; feeling informed and respected; communication makes a huge difference

**Expected summary:** The customer praises the clinic for clear communication, patient listening, understandable explanations, and a respectful appointment experience. The review emphasizes that the staff reduced anxiety and helped the customer feel informed. Overall, the experience was positive because the clinic handled both logistics and care with empathy.

**Notes:** The key sentiment is in service phrases, not just obvious words like "great" or "excellent."

## 8. Negative: Subscription Cancellation Friction

**Review text:** Canceling this subscription was way harder than signing up. The website sent me in circles, the cancellation button disappeared on mobile, and support replied with a generic message that did not answer my question. I was charged again after I thought the account was closed. That feels misleading and unfair.

**Expected sentiment:** negative

**Expected sentiment keywords/phrases:** way harder than signing up; sent me in circles; cancellation button disappeared; generic message; did not answer my question; charged again; misleading and unfair

**Expected summary:** The customer is frustrated by a difficult cancellation process and poor support. They describe confusing website flows, a missing mobile cancellation button, generic help responses, and an unexpected charge after they believed the account was closed. Overall, the review is negative because the customer feels misled and treated unfairly.

**Notes:** The phrase "charged again after I thought the account was closed" is important evidence and should appear in the summary.

## 9. Neutral: Hotel Stay With Trade-Offs

**Review text:** The hotel was clean and close to the conference center, which was convenient. The room was smaller than expected, and the hallway noise was noticeable at night. Breakfast was basic but acceptable. I would stay again for location, but I would not choose it for a relaxing trip.

**Expected sentiment:** neutral

**Expected sentiment keywords/phrases:** clean; close to the conference center; convenient; smaller than expected; hallway noise was noticeable; basic but acceptable; stay again for location; not choose it for a relaxing trip

**Expected summary:** The customer reports a practical but limited hotel stay. They liked the cleanliness and convenient location near the conference center, but noted a small room, nighttime hallway noise, and basic breakfast. Overall, the review is neutral because the hotel works for convenience but not for comfort or relaxation.

**Notes:** This should not be classified as fully positive just because the customer would stay again for a specific use case.

## 10. Negative: Good Idea, Broken Execution

**Review text:** The app has a useful idea, but the execution is poor. It crashed three times while I was uploading receipts, the totals did not match my bank statement, and the export file was missing two transactions. Support was polite, but they could not explain what went wrong. I cannot trust it with financial records.

**Expected sentiment:** negative

**Expected sentiment keywords/phrases:** execution is poor; crashed three times; totals did not match; missing two transactions; could not explain what went wrong; cannot trust it with financial records

**Expected summary:** The customer sees value in the app concept but has lost trust because of crashes, incorrect totals, missing export data, and unresolved support answers. The review shows that reliability and accuracy problems outweighed polite support. Overall, the sentiment is negative because the app failed in a high-trust financial workflow.

**Notes:** The model should detect that "useful idea" is not enough to overcome the critical reliability and trust concerns.
