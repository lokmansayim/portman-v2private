# WhatsApp Conversational Design for a B2B Prefab Dealer Assistant (as of Sept 2026)

Scope: how to move a Turkish dealer from a vague request ("80 m² tek kat prefabrik istiyorum") to a producible configuration on WhatsApp, using the LLM plus WhatsApp Cloud API native interactive features; what Meta currently allows and charges; dialogue-policy evidence; real deployments; guardrails. Research date: 2026-09-21. Primary Meta docs were fetched where possible; several Meta pages rate-limited (HTTP 429), in which case limits are cross-checked against two or more BSP/vendor documentation pages and flagged as secondary.

---

## Key Question 1 — What Meta currently allows: interactive lists, reply buttons, CTA URL buttons, Flows, catalogs; limits; approval; 24h window

### Takeaway
Inside an open 24-hour customer service window (opened by any inbound dealer message and reset by each new one) the business may send free-form "service messages" including interactive lists (max 10 rows total across up to 10 sections), reply buttons (max 3), CTA-URL buttons (1 URL), single/multi-product catalog messages (up to 30 products), and Flow messages (form screens) — none of these need Meta template approval when sent inside the window. Outside the window only pre-approved templates can be sent (a template may carry a FLOW button, quick-reply buttons, or a multi-product body).

### Cited Findings

**Customer service window (primary Meta doc)**
- "When a WhatsApp user messages you or calls you, a 24-hour timer called a customer service window starts." "If the user messages or calls you again before the timer expires, the timer resets to 24 hours." "When the window closes, you can only send pre-approved template messages." Service messages "are free-form and don't require pre-approval." The page lists interactive messages (lists, reply buttons, flows, location requests, reactions) among service message types available during open windows — [Meta: Service messages](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages)
- Kommo's Turkish-language summary of the same rule: "Normal (serbest biçimli) mesajlar ücretsiz olarak gönderilebilir, ancak bunun için müşterinin son 24 saat içinde size mesaj atmış olması gerekir"; outside the window "işletmelerin onaylanmış WhatsApp şablon mesajlarını kullanması gerekir" — [Kommo TR support](https://support.kommo.com/docs/tr/whatsapp-business-iin-gncellenen-fiyatlandrma-kurallar)

**Interactive reply buttons (primary Meta doc)**
- "up to three predefined replies"; button title max "20 characters"; button ID max "256 characters"; body max "1024 characters" (URLs auto-hyperlinked); footer max "60 characters"; header types: "document," "image," "text," and "video"; media header via uploaded media ID (preferred) or URL ("not recommended") — [Meta: Interactive reply buttons messages](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/interactive-reply-buttons-messages)

**Interactive list messages (Meta page returned HTTP 429 twice; limits below are from three independent secondary sources that agree)**
- "up to 10 sections in a single list message"; "maximum of 10 rows in total across all sections"; row titles "up to 24 characters"; list rows are "text-only options" — "Media attachments, phone numbers, and external links are not supported within list items" — [WATI](https://www.wati.io/en/blog/whatsapp-list-messages-benefits/)
- Section title max 24 chars; row title max 24; row description max 72; header text max 60 — [CM.com developer docs](https://developers.cm.com/messaging/docs/whatsapp-interactive-messages)
- List button text max 20 chars; section title 24; row title 24; row description 72; row ID 200 chars; "Limited to 10 rows across all sections"; interactive body max 1024; header 60; footer 60; plain text message max "4096 characters" — [PickyAssist limits page](https://help.pickyassist.com/general-guidelines/character-limits-whatsapp)
- engageSPARK's platform page (note: their 1,600-char text limit is a platform/Twilio-style cap, not Meta's 4096) also lists: list "up to 10 items", titles 24, descriptions 72; buttons "up to 3", 20 chars; document max file size "16 MB"; image "5 MB" — [engageSPARK](https://www.engagespark.com/support/whatsapp-business-limits/)

**CTA URL button and carousel**
- "Only a single URL button is supported by WhatsApp in a call-to-action URL button message"; media carousel messages "between 2 and 10 cards" — [CM.com developer docs](https://developers.cm.com/messaging/docs/whatsapp-interactive-messages)
- Meta changelog Aug 27, 2025: call "Permission requests became available as interactive message types" (new interactive type) — [Meta changelog](https://developers.facebook.com/documentation/business-messaging/whatsapp/changelog)

**Catalog / product messages (primary Meta doc)**
- Multi-product messages: "up to 30 products organized into sections"; catalog must be "connected to your WhatsApp Business account (WABA)", uploaded via Commerce API or Meta Commerce Manager; customers can add "up to 99 units of each single catalog item", "No limit on the number of distinct items", "Only one cart is created per chat thread"; products undergo automatic review and violating items are "flagged"; businesses can appeal via Commerce Manager — [Meta: Catalogs overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/catalogs/catalogs-overview/)
- 360dialog documents catalogs/product messages for Cloud API clients (listed in search; not fetched) — [360dialog Catalogs](https://docs.360dialog.com/docs/messaging/catalogs)

**WhatsApp Flows (form screens)**
- Two delivery methods: "Template-based (business-initiated)" — flow attached via a "FLOW" button type, "Ensure that your template passes all required reviews so that status is APPROVED"; and "Interactive messages (user-initiated)" — "Flows send as interactive messages in ongoing conversations using a CTA button that triggers the Flow." `flow_action` is `"navigate"` (default) or `"data_exchange"`; `flow_message_version` must be `"3"`; `mode` is `"draft"` or `"published"` (default); "CTA text length is advised to be 30 characters or less (no emoji)" — [Meta: Sending a Flow](https://developers.facebook.com/documentation/business-messaging/whatsapp/flows/guides/sendingaflow)
- Infobip (Meta BSP): template flow messages "Do not require a 24-hour customer service window between you and the recipient"; free-form flow messages "can only be sent to a user when a customer service window is open"; before publishing you must "Resolve all validation errors and publishing checks"; two types: "Without Endpoint" (static) and "With Endpoint" ("for dynamic elements, such as data population or navigation control"); flow JSON max "10 MB"; supported components: text fields, radio buttons, checkboxes, menus (dropdowns), date pickers, calendars, navigation lists, chips, If/Switch conditional logic, opt-ins, footers, embedded links, media upload — [Infobip: Build WhatsApp Flows](https://www.infobip.com/docs/whatsapp/whatsapp-flows/build-whatsapp-flows)
- Flow JSON component limits (secondary, community spec transcribed from Meta reference): "maximum number of components per screen is 50"; CheckboxGroup/RadioButtonsGroup options "Min 1, Max 20"; Dropdown "Max 200 (no images), Max 100 (with images)"; ChipsSelector "Min 2 options, Max 20 options"; TextInput max chars "Default: 80"; TextArea "Default: 600"; heading/subheading 80; body 4096; caption 409; endpoint should answer in "~10–15s" with `version`, `screen`, `data` fields (missing `version` causes silent empty-data failure) — [gokapso whatsapp-flows-spec](https://github.com/gokapso/agent-skills/blob/master/skills/integrate-whatsapp/references/whatsapp-flows-spec.md)
- Max screens: Meta validation error text "Maximum number of screens allowed per Flow is 100" — [Heltar](https://www.heltar.com/blogs/how-to-fix-maxscreensnumber-error-in-whatsapp-flows-2025-limit-hit-cmbz8mr660003m7n4xmvjbbvb)

**Business-initiated volume tiers**
- Messaging limits for business-initiated (template) conversations: "Five tiers: 250, 1k, 10k, 100k, and unlimited" unique contacts in a "24h moving window"; templates allow "up to 100 personalizations / variables" — [engageSPARK](https://www.engagespark.com/support/whatsapp-business-limits/)

### Inferences
- For the prefab use case, the entire guided configuration can run as free-form service messages as long as the dealer keeps replying (each reply resets the 24h timer). The only step that risks falling outside the window is delivering the finished PDF/quote if generation takes long or the dealer goes quiet; that delivery then needs an approved utility template (e.g., "Teklifiniz/planınız hazır" with a document header or a URL button).
- Interactive list (10 rows, 24-char titles, 72-char descriptions) fits "pick the nearest catalog model" or "choose roof type / room count" but cannot show images; a multi-product message (up to 30 products, images+price from Commerce Manager) is the only native way to show model photos in a tappable list, but it requires maintaining a Commerce Manager catalog that passes Meta's automatic product review.
- Reply buttons (max 3, 20 chars) map naturally to Turkish confirmation triads such as "Onayla / Değiştir / Yetkiliye bağlan" — keep labels ≤20 characters including Turkish diacritics.
- A Flow (form) can collect the whole slot set in one screen or 2–3 screens (area, floors, rooms, roof, usage, delivery province) with dropdowns up to 200 options and `data_exchange` to validate against the catalog in real time; it needs no Meta review when sent inside the window, only Meta's automated publishing checks.

### Gaps
- Could not fetch the primary Meta interactive-list page (HTTP 429); the 10-section/10-row/24/72-char limits are corroborated by three vendor docs but not directly quoted from Meta here.
- Meta's WhatsApp Flows overview page returned essentially empty content; the 100-screen and 50-component limits come from secondary sources.
- Whether Flows are subject to any regional availability restriction for Turkey was not confirmed (no source found stating a restriction).

---

## Key Question 2 — WhatsApp Business Platform pricing 2025–2026 (per-message model, free window, Turkey rates)

### Takeaway
Since July 1, 2025 Meta bills per delivered template message by category (marketing / utility / authentication), while service (free-form) messages and in-window utility templates have been free; on October 1, 2026 service messages and in-window utility templates become billable per delivered message at the market's utility rate, with BSPs reporting a 1,000-free-service-messages-per-phone-number-per-month allowance. Published post-Oct-2026 Turkey rates (BSP-transcribed) are about USD 0.0109 marketing and USD 0.0009 utility/authentication/service — among the lowest globally.

### Cited Findings

**Model and free rules (primary Meta doc)**
- "Effective July 1, 2025, Meta charges on a per-message basis"; categories: Marketing, Utility, Authentication, Service. "All non-template messages are free" within an active customer service window; "Utility templates delivered within an open customer service window are free"; "All messages are free for 72 hours" in a Free Entry Point window from Click-to-WhatsApp ads. Volume tiers lower utility/authentication rates by monthly volume aggregated "across all of a business portfolio's WABAs" per market-category; "Tiers reset monthly". "Effective October 1, 2025," Turkey received "Lower utility and authentication rates." 2026 items: Marketing Messages API "max-price per marketing message delivery"; "New AI Provider pricing policy effective February 16, 2026"; Brazil BRL billing July 1, 2026; rate card updates scheduled Oct 1, 2026 — [Meta: Pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)
- Changelog: Nov 1, 2024 "Service conversations are now free for all businesses, including via AI-enabled conversational experiences"; Jul 1, 2025 per-message pricing; Oct 1, 2025 utility/auth rate changes in several countries; Apr 1, 2026 "Updated per-message rate cards with rate changes for Saudi Arabia, India, Pakistan, and Turkey" and 8 new billing currencies (AED, ARS, CLP, COP, MYR, PEN, SAR, SGD) — [Meta changelog](https://developers.facebook.com/documentation/business-messaging/whatsapp/changelog)

**October 2026 change for service / in-window utility / AI agents (primary Meta doc)**
- Aug 1, 2026: Meta begins charging for "Meta Business Agent messages"; Oct 1, 2026: service messages start being charged and utility messages inside the 24h window become paid. Service messages: "Meter: Per message. Rate: By market, rates for service messages are the same as the rates for utility and authentication messages." "Meta does not offer volume tiers for service messages." Service messages marked "Free in 24-hour customer service window — Free until October 1, 2026"; "Messages sent within the 72-hour free entry point window ... remain free." Meta Business Agent: "$2.00 USD per 1M tokens", "approximately 4–5 cents (USD) per message" at "about 20,000–25,000 tokens". Messages powered by "a 3rd-party AI solution" incur "separate charges for AI usage from the AI provider and message delivery from the messaging solution provider." Meta will announce Oct 1, 2026 rates by Sept 1, 2026 — [Meta: Upcoming pricing updates for Meta Business Agent, service and utility messages](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages)
- BSP summaries: "Service messages ... currently free but changing October 1, 2026"; Meta Business Agent "billed differently from service messages" on a token basis — [CM.com pricing blog](https://www.cm.com/blog/whatsapp-business-platform-pricing/)

**Free allowance (BSP sources; NOT present on the Meta page fetched — treat as reported, verify with your BSP)**
- "Every business phone number receives 1,000 free service messages each month, charged from the 1,001st, with no rollover and a monthly reset"; per phone number, not per WABA; user inbound messages free; Meta Business Agent messages charged for tokens even inside the 72h window; example high-rate markets Germany $0.055, Netherlands $0.050 — [360dialog](https://360dialog.com/blog/whatsapp-service-message-charging-october-2026/)
- "1,000 free service messages per month" per phone number; UAE example "(10,000 − 1,000) × $0.0157 = $141.30"; rate-card examples for Oct 2026: Morocco utility $0.0040→$0.0230, Kuwait $0.0091→$0.0440, Sri Lanka $0.0113→$0.0020; recommends businesses "optimize replies to reduce unnecessary messages" — [YCloud](https://www.ycloud.com/blog/whatsapp-api-message-pricing-update-effective-october-1-2026)

**Turkey rates (secondary transcriptions of Meta rate cards; dates differ)**
- Rate card "Effective Date: October 1, 2026" for Turkey: Marketing $0.0109; Utility $0.0009; Authentication $0.0009; Service $0.0009 (after 1,000 free/number/month); "Turkey offers the lowest marketing rates globally on this rate card" — [Whautomate pricing by country](https://whautomate.com/whatsapp-business-api-pricing)
- Older (undated) EUR card for Turkey: Marketing €0.01730; Utility €0.00850; Authentication €0.00850; Service free within 24h — [Messaggio Turkey](https://messaggio.com/pricing-whatsapp/turkey/)
- Kommo TR: as of Apr 1, 2026 "Oran düşüşleri" for "Türkiye'de hizmet ve kimlik doğrulama mesajları" (rate decreases for service and authentication in Turkey) — [Kommo TR support](https://support.kommo.com/docs/tr/whatsapp-business-iin-gncellenen-fiyatlandrma-kurallar)
- Turkish-language rate pages exist at VatanSMS ("Meta Resmî Tarifeler") and WaMessage but were not fetched — [VatanSMS](https://www.vatansms.com/whatsapp/business-api-fiyatlar/), [WaMessage](https://wamessage.app/whatsapp-api-fiyat-hesaplama.php)

### Inferences
- Until Oct 1, 2026 the entire dealer dialogue (LLM replies, lists, buttons, flows, PDF delivery inside the window) costs nothing at Meta level; from Oct 1, 2026 every delivered bot bubble beyond 1,000/month per number costs roughly the Turkey utility rate (~$0.0009 if the Whautomate transcription is correct), i.e., 10,000 bot messages ≈ $8–9/month — negligible, but the meter is per delivered message, so a chatty bot that splits one answer into five bubbles pays 5×. Design implication: consolidate each turn into one message (body ≤1024 chars for interactive, ≤4096 for text) and prefer a single list/flow over multiple text questions.
- Delivering the PDF plan/quote after the window closes requires a utility template; in Turkey that is ~$0.0009 per delivery on the Oct-2026 card — cost is not a constraint; template approval lead time is.
- Because Meta treats third-party AI as "separate charges from the AI provider", the LLM cost (per token) will dominate messaging cost; the deterministic menu steps (list/button taps) generate no LLM cost, another reason to route routine slot collection through native components.

### Gaps
- Could not fetch Meta's official rate-card page (business.whatsapp.com/products/platform-pricing) — the Turkey numbers are vendor transcriptions with inconsistent dates/currencies (EUR 0.0173 vs USD 0.0109 marketing); verify against the current Meta CSV rate card before quoting to management.
- The "1,000 free service messages per phone number per month" allowance is reported by multiple BSPs (360dialog, YCloud, Whautomate) but did not appear on the Meta page fetched; status should be confirmed.
- Details of the "AI Provider pricing policy effective February 16, 2026" were not retrieved.

---

## Key Question 3 — Dialogue policy evidence: slot filling vs open dialogue, one question at a time, presenting 3 options, confirmation before costly actions

### Takeaway
Practitioner guidance (Google conversation design, Botpress) converges on: implicit confirmation by default, explicit confirmation only before hard-to-undo or costly actions; short turns (1–2 sentences); 2–3 tappable choices per step. Academic evidence supports asking clarifying questions on ambiguous requests (+3–5% on relevant metrics) and shows choice overload is real mainly when options are complex, hard to compare and the user has uncertain preferences — exactly the prefab-configuration situation — so a small, curated option set beats a long list.

### Cited Findings

**Confirmation policy**
- Implicit confirmation: "Use most of the time, not to confirm the user's input per se, but to confirm the parameters that were said or implied." Explicit confirmation: "Double-check with the user prior to performing an action that would be difficult to undo, for example, deleting user data, completing a transaction, etc."; for parameters, explicit "only when the cost of misunderstanding the user is high, for example, names, addresses, texts to be shared on the user's behalf." — [Google Assistant conversation design: Confirmations](https://developers.google.com/assistant/conversation-design/confirmations?hl=en)

**Short turns, few options, fallback**
- "Keep responses short and focused. Aim for 1–2 sentences at a time."; use "progressive disclosure by offering 2–3 choices for users to choose from"; instead of open-ended prompts, "try, 'Are you looking to book an appointment, ask about hours, or talk to support?'"; fallback example "I didn't understand that, but I can connect you to support or you can try a different question."; "Pick a voice, a tone, and a style — and stick with it." — [Botpress: Conversation design 2026](https://botpress.com/blog/conversation-design)
- List messages "most effective for menus with up to 10 options"; reply buttons "up to three options"; claimed "significantly higher response and conversion rates compared to text-only messages" (no numbers given) — [Infobip: New WhatsApp message types](https://www.infobip.com/blog/new-whatsapp-message-types)
- Flows design tip: start with "a simple 2–3-screen flow" and iterate; "a 3-screen lead capture flow"; "simplify forms, reduce fields, and optimize CTAs"; track "step completion and abandonment per screen" — [Infobip: WhatsApp Flows](https://www.infobip.com/blog/whatsapp-flows)

**Clarifying questions vs presupposing an interpretation (LLM research)**
- LLMs "must often respond to highly ambiguous user requests" and tend to "respond by presupposing a single interpretation"; training with simulated future turns to ask clarifying questions gave "5% improvement in F1" on ambiguous open-domain QA and "3% improvement in accuracy" in deciding whether clarification is necessary (ICLR 2025) — [Zhang et al., Modeling Future Conversation Turns](https://mlanthology.org/iclr/2025/zhang2025iclr-modeling/)
- Zero-shot slot filling with LLMs in industrial dialogue systems (COLING 2025 industry track) — [ACL Anthology PDF](https://aclanthology.org/2025.coling-industry.59.pdf) (listed; not fetched)

**Choice architecture / how many options**
- Original jam study (Iyengar & Lepper 2000): 24 vs 6 varieties — ~60% vs ~40% stopped, but "only about 3 percent" bought from the 24-jam display vs "about 30 percent" from the 6-jam display. Scheibehenne et al. 2010 meta-analysis (50 studies, ~5,000 participants): average effect of larger choice sets "approximately d = 0 — essentially zero". Chernev, Böckenholt & Goodman 2015: overload appears reliably under "high complexity" (options "differed on multiple attributes, or were difficult to compare"), "decision difficulty", "preference uncertainty", and "effort-minimization goals"; "When all four moderators were present at high levels, the choice-overload effect was substantial (d ≈ 0.5 to 0.6)." — [Atticus Li: Jam study and moderators](https://atticusli.com/replication-crisis/choice-overload-jam-study/)

**Conversational recommender systems review**
- Systematic review across classical and LLM-powered CRS: some systems used "slot-filling strategies" and "mixed-initiative capabilities"; the review "does not provide specific metrics on optimal turn counts"; "Despite LLM flexibility, systems did not modulate initiative, verbosity, or content selection based on evolving user inputs"; only two LLM-powered CRS were evaluated; one hybrid (retrieval-based candidates + GPT-3.5 free-form responses) had "22% of recommendations were not on the platform"; "Hallucinated content risks undermining trust"; "LLM-powered CRS introduce further challenges, including epistemic opacity and verbosity" — [arXiv 2508.02096 (systematic review)](https://arxiv.org/html/2508.02096v2)

### Inferences
- Prefab models differ on many attributes (m², floors, roof, wall panel, rooms, delivery) and dealers relay end-customer wishes with uncertain preferences — all four Chernev moderators are high, so choice overload is expected; present at most 3 candidate models per turn (reply buttons) or ≤10 in a list, never the full catalog.
- The "one question at a time" rule should be applied per missing slot but batched where WhatsApp offers a native container: one Flow screen with 4–6 fields is one "question" from the dealer's perspective and yields validated structured data in a single turn.
- Costly generation (floor plan render, PDF quote) and irreversible steps (sending the quote to the end customer, creating an order) meet Google's "difficult to undo / transaction" threshold — use explicit confirmation with a summary card + 3 buttons before generating.
- Ambiguity in "80 m² tek kat" (interior vs gross area, number of rooms, bathroom count, purpose) is exactly the case where an LLM will presuppose; the LLM should be prompted to extract slots and ask, not to guess.

### Gaps
- No controlled study was found that measures completion or accuracy of "one question at a time" vs "all-at-once form" specifically on WhatsApp; the Flows guidance (2–3 screens) is practitioner advice, not a published experiment.
- The CRS review is explicit that turn-level evaluation of clarification strategies is missing in the literature.

---

## Key Question 4 — LLM-guided product configurators / CPQ + LLM (2025–2026)

### Takeaway
Research and vendor practice both treat the LLM as an interpreter/explainer layered on a deterministic configuration/catalog model, not as the configurator itself: hallucinated, constraint-violating configurations are the documented failure, and the fix is retrieval of verified catalog/knowledge-graph facts into the prompt plus post-generation validation against constraints.

### Cited Findings
- LLMs in product configuration produce "outputs that appear plausible but violate domain constraints or factual correctness"; proposed two-stage remedy: "Knowledge-Aware Inference" (RAG injecting verified knowledge-graph facts) and "Knowledge-Aware Validation" (post-processing outputs against KG constraints), yielding a "KG-aware assistant capable of intelligent interpretation and constraint-compliant generation"; published May 1, 2026 (Springer, Integrated Systems: AI-Augmented Engineering); the abstract reports no quantitative results — [Multi-stage Knowledge Graph-Augmented LLMs for Reliable Product Configuration](https://link.springer.com/chapter/10.1007/978-3-032-21981-7_4)
- Related chapter "Configuration with Generative AI" in a 2026 Springer volume (listed; not fetched) — [Springer](https://link.springer.com/chapter/10.1007/978-3-032-17163-4_8)
- Usability analysis of configurator UIs with multimodal LLMs (arXiv, 2026; listed, not fetched) — [arXiv 2605.29456](https://arxiv.org/abs/2605.29456)
- CPQ vendors position guided selling as needs-based questioning that narrows a rules-based configurator (Tacton, Xait, Elfsquad, Zoovu pages listed in search; marketing content, no measured results extracted) — [Tacton CPQ guided selling](https://www.tacton.com/cpq-blog/cpq-and-guided-selling-empowering-manufacturing-customers/), [Elfsquad: What is guided selling](https://www.elfsquad.io/guides/guided-selling)
- The CRS review's hybrid system (retrieval candidates + LLM wording) still produced "22% of recommendations were not on the platform" — evidence that generation must be constrained to catalog IDs, not just "informed" by retrieval — [arXiv 2508.02096](https://arxiv.org/html/2508.02096v2)

### Inferences
- Architecture that follows the evidence: LLM → structured slot JSON (area, floors, rooms, roof, wall type, usage, province) → deterministic catalog matcher returns the top-3 nearest producible models with IDs → LLM only phrases the options and asks the next question; any price/lead-time/dimension text is templated from the catalog record, never generated.
- A WhatsApp Flow with `data_exchange` is the native place to run the validation stage (reject impossible combinations like 80 m² with 5 bedrooms before the dealer submits).

### Gaps
- No peer-reviewed evaluation of an LLM-driven conversational configurator with reported validity/accuracy rates was found in the fetched material; the 2026 Springer chapter is conceptual in its abstract.
- No CPQ vendor published time-to-quote deltas attributable to LLM guidance in the sources fetched.

---

## Key Question 5 — Documented B2B / manufacturing / construction WhatsApp sales assistants (Turkey and global), and what failed

### Takeaway
Concrete, metric-bearing case studies of B2B dealer assistants on WhatsApp are scarce in public sources: Turkish vendor pages (CBOT, Sestek, Insider, Kommo, CollectAction) describe capabilities and B2C examples rather than dealer deployments with numbers; global examples (Schneider Electric India's "1-min BOQ ordering", BeatRoute for building-materials dealers) are descriptive. The best-documented lessons come from failures: Air Canada (liable for chatbot-invented policy) and Chevrolet of Watsonville (prompt-injected "$1" offer).

### Cited Findings

**Turkey**
- Turkey has "%88 penetrasyon oranı ile 8. sırada" WhatsApp penetration (88%, 8th globally); CBOT's WhatsApp page describes generic customer-service benefits and links to customer stories but names no dealer/B2B deployments with metrics — [CBOT WhatsApp Business API page](https://www.cbot.ai/tr/yapay-zeka-tabanli-whatsapp-business-chatbotlarimiz/)
- Turkish order-bot guide: "Müşteri 'Fiyat listesi', 'Sipariş vermek istiyorum' gibi mesajlar attığında bot devreye girer, kategorileri gösterir, ürünleri listeler ve ödeme adımına yönlendirir"; bot "tekrar eden soruların çoğunu otomatik yanıtlıyor"; example Tesettür Island: "Müşterilerimiz genellikle bedene veya stoğa dair soru soruyordu" — B2C, no conversion numbers — [CollectAction](https://collectaction.com/blog/whatsapp-toplu-mesaj-ve-siparis-botu-rehberi/)
- Insider acquired Turkish conversational platform MindBehind (Jan 2023) — relevant to the Turkish WhatsApp vendor landscape — [Webrazzi](https://webrazzi.com/2023/01/10/insider-diyalog-bazli-mesajlasma-platformu-mindbehindi-satin-aldi/)
- Invekto's "WhatsApp Business ile B2B Müşteri Yönetimi... Bayi ve Tedarikçi İletişim Rehberi" returned HTTP 410 (removed) — [Invekto (dead link)](https://invekto.com/blog/whatsapp-business-b2b-musteri-yonetimi-bayi-tedarikci)
- Sestek's public pages found were sector-generic (insurance, customer care), no dealer case — [Sestek](https://www.sestek.com/)

**Global manufacturing / building materials**
- Schneider Electric India "Koko 2.0" WhatsApp chatbot for "1-min BOQ ordering": customers "download the template sheet and fill in the details", "The chatbot can also guide customers on how to format the BOQ template", then "upload the Excel sheet in CSV form directly to the chatbot"; audience "distributors to shop owners"; no adoption or time-saved metrics published — [Schneider Electric eShop blog](https://eshop.se.com/in/blog/post/revolutionizing-b2b-industry-with-1-min-boq-ordering-on-whatsapp.html)
- BeatRoute (building-materials dealer sales on WhatsApp): dealers "only open the dealer app to place orders and nothing else" whereas WhatsApp is "the one app your dealers already open several times every day"; workflows: order updates, scheme notifications, payment reminders, product launches; no metrics on the page — [BeatRoute webinar](https://beatroute.io/africa/webinars/whatsapp-dealer-sales-building-materials/)
- Unilever's eB2B retailer platform (app-based, not WhatsApp): "500,000 retailers, 600 distributors and over 6,000 sales reps", "75,000 orders daily", "€2.5 billion" annualized sales, AI assortment recommendations for "15-20 minute retailer visits" — useful benchmark for structured self-ordering at scale — [Unilever news 2025](https://www.unilever.com/news/news-search/2025/how-ai-and-ecommerce-tools-are-transforming-emerging-market-retail/)
- nfuse (ex-Coca-Cola execs) raised $2M for AI-powered WhatsApp ordering in FMCG trade (search-listed; not fetched) — [TechFundingNews](https://techfundingnews.com/nfuse-lands-2m-from-eleven-ventures-launchub-to-grow-ai-powered-whatsapp-ordering-in-fmcg-trade/)
- A "4 WhatsApp chatbot examples for the construction materials industry" article contains only use-case categories (ordering, catalog recommendations, support, lead gen) — no company names or results — [mcomtech](https://www.mcomtech.ch/post/4-whatsapp-chatbot-examples-for-the-construction-materials-industry-in-emerging-markets)
- Infobip customer claims for Flows (B2C): Nissan "80% session engagement rate"; Apollo "72% increase in average revenue per order"; Mukuru "92% read rates"; Angel One "35% open rate" — [Infobip Flows blog](https://www.infobip.com/blog/whatsapp-flows)

**Failures with legal / reputational consequences**
- Moffatt v. Air Canada (BC Civil Resolution Tribunal, Feb 14, 2024): chatbot wrongly said bereavement fares could be claimed within 90 days; tribunal found "negligent misrepresentation", awarded ≈ CAD 650 + interest + fees; "Air Canada could not separate itself from the AI chatbot, which was integrated in its own website"; company "bore responsibility for all the information on its website, whether it came from a static page or a chatbot" — [American Bar Association](https://www.americanbar.org/groups/business_law/resources/business-law-today/2024-february/bc-tribunal-confirms-companies-remain-liable-information-provided-ai-chatbot/)
- Chevrolet of Watsonville (Dec 18, 2023; vendor Fullpath on ChatGPT): user prompt-injected the bot to agree with anything and end with "legally binding offer"; bot replied "That's a deal, and that's a legally binding offer – no takesies backsies" for a ~$76,000 Tahoe at $1; dealership did not honor it; vendor CEO acknowledged the vulnerability — [AI Incident Database #622](https://incidentdatabase.ai/cite/622/)

### Inferences
- Absence of public Turkish B2B dealer WhatsApp case studies with numbers is itself a finding: the company should plan to instrument its own baseline (time-to-quote, turns-to-configuration, handoff rate) rather than rely on vendor benchmarks.
- The Schneider pattern (structured upload + bot guidance on format) suggests a "document-first" alternative path for dealers who already have a sketch/BOQ: accept a PDF/photo and extract slots, then confirm — complementary to the guided chat.
- Both failure cases share a root cause: the model was allowed to state commitments (policy, price) not grounded in a system of record. For a quoting assistant, price and model existence must be system-generated fields, and the bot must be prompted that it cannot make offers.

### Gaps
- No Turkish B2B/dealer WhatsApp deployment with measured results (completion rate, time-to-quote) was found from Sestek, Insider, Botego, CBOT, Kommo or Twilio/Infobip Turkey pages; Invekto's dealer guide is offline.
- Schneider and BeatRoute publish no adoption or time metrics; Infobip's Flow metrics are engagement/read rates in B2C, not configuration completion.

---

## Key Question 6 — Combining LLM free-text understanding with deterministic menus; guardrails; message-length and tone norms

### Takeaway
The workable pattern is "LLM as parser and narrator, catalog as source of truth, native components as the default input": every step offers tappable options (list/buttons/flow) but accepts free text, which the LLM maps to the same slot schema; anything numeric or contractual (price, dimensions, lead time, model name) is rendered from catalog records; explicit confirmation gates costly generation; a human-handoff button is always present. WhatsApp itself constrains lengths (interactive body ≤1024 chars, button labels ≤20, list rows ≤24/72), and practitioner norms push 1–2 sentences per bubble.

### Cited Findings
- Interactive replies come back with developer-set identifiers: reply-button ID up to "256 characters"; list row ID up to "200 characters" — enabling deterministic routing of taps while free text goes to the LLM — [Meta reply buttons](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/interactive-reply-buttons-messages), [PickyAssist limits](https://help.pickyassist.com/general-guidelines/character-limits-whatsapp)
- Flows with an endpoint support "data population or navigation control" (dynamic option lists, server-side validation) — [Infobip Flows docs](https://www.infobip.com/docs/whatsapp/whatsapp-flows/build-whatsapp-flows); endpoint must respond with `version`, `screen`, `data` and within ~10–15 s — [gokapso spec](https://github.com/gokapso/agent-skills/blob/master/skills/integrate-whatsapp/references/whatsapp-flows-spec.md)
- The CRS review finds true LLM+policy hybrids "remain largely unimplemented" in research and that LLM systems "did not modulate initiative, verbosity, or content selection" — [arXiv 2508.02096](https://arxiv.org/html/2508.02096v2)
- Grounding + validation against a knowledge graph is the proposed remedy for constraint-violating LLM configurations — [Springer 2026](https://link.springer.com/chapter/10.1007/978-3-032-21981-7_4)
- Liability: a company "bore responsibility for all the information ... whether it came from a static page or a chatbot" — [ABA on Moffatt v. Air Canada](https://www.americanbar.org/groups/business_law/resources/business-law-today/2024-february/bc-tribunal-confirms-companies-remain-liable-information-provided-ai-chatbot/); prompt injection produced a "legally binding offer" for $1 — [AIID #622](https://incidentdatabase.ai/cite/622/)
- Message norms: "Aim for 1–2 sentences at a time"; "2–3 choices"; explicit fallback with handoff offer; consistent tone — [Botpress](https://botpress.com/blog/conversation-design)
- Hard limits: text message max 4096 chars; interactive body 1024; header/footer 60; button title 20; list row title 24 / description 72 — [PickyAssist](https://help.pickyassist.com/general-guidelines/character-limits-whatsapp); document attachment up to 16 MB — [engageSPARK](https://www.engagespark.com/support/whatsapp-business-limits/)
- Cost lever after Oct 1, 2026: service messages metered "Per message" — [Meta non-template pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages); BSP advice to "optimize replies to reduce unnecessary messages" — [YCloud](https://www.ycloud.com/blog/whatsapp-api-message-pricing-update-effective-october-1-2026)

### Inferences (design recommendations grounded in the above)
- Dual-input every step: send a list/button/flow AND tell the LLM the current slot schema; if the dealer types "iki oda olsun, çatı sac", the LLM fills `rooms=2, roof=sac` and the bot skips those questions (Google's implicit confirmation: restate in the next prompt, e.g., "2 oda, sac çatı — kaç banyo?").
- Never let the LLM emit a number that is not in the retrieved catalog record: prices, m², lead times and model codes are inserted by code into a fixed Turkish template; the LLM's output is constrained to slot JSON + short connective text. Add a system rule "teklif/fiyat/indirim taahhüdü verme; fiyat yalnızca sistem hesaplar" and a refusal path for "en ucuzu kaç lira" until configuration is confirmed.
- Explicit confirmation before generation: one summary message (≤1024 chars) + reply buttons "Onayla" / "Değiştir" / "Yetkili" (all ≤20 chars); generate the PDF only on "Onayla"; log the confirmed JSON as the order-of-record.
- Escalation rules: (a) dealer taps "Yetkili" at any time; (b) two consecutive unparsed free-text turns; (c) request outside catalog envelope (e.g., >2 floors, custom span) — hand off with the partially filled JSON so the human doesn't restart.
- Turkish tone for dealers ("bayinin dili"): short, direct, second-person formal ("siz"), trade vocabulary (tek kat, sac çatı, sandviç panel, teslim süresi), no marketing fluff; one question per bubble; use the 60-char footer for the persistent hint "Yazabilir veya seçebilirsiniz."
- Window management: if PDF generation exceeds a few minutes or the dealer stops replying, deliver via an approved utility template ("Talebiniz için plan/teklif hazır: {{model}}") with a document header; keep this template pre-approved.

### Gaps
- No published Turkish-language style guide for B2B dealer messaging on WhatsApp was found; the tone recommendations are inferred from generic conversation-design guidance plus WhatsApp's character limits.
- No source quantified how much a "tap-or-type" dual-input design improves completion vs. menu-only or LLM-only on WhatsApp.

---

## Key Question 7 — Measured effects (completion rates, time-to-quote) where available

### Takeaway
Hard numbers for guided configuration on WhatsApp are essentially unpublished; what exists are (a) B2C engagement/read metrics for Flows and interactive messages from BSP marketing, (b) LLM-research deltas for clarification (+3–5%), (c) choice-overload effect sizes (d≈0.5–0.6 under high complexity), and (d) an offline benchmark that reducing options raised conversion from ~3% to ~30% in the classic jam study (with a null average effect across the literature).

### Cited Findings
- Infobip Flows customers: Nissan "80% session engagement rate"; Apollo "72% increase in average revenue per order"; Mukuru "92% read rates"; Angel One "35% open rate" — [Infobip](https://www.infobip.com/blog/whatsapp-flows)
- Interactive lists/buttons: "significantly higher response and conversion rates compared to text-only messages" — no figure — [Infobip](https://www.infobip.com/blog/new-whatsapp-message-types)
- Clarifying-question training: "+5% F1", "+3% accuracy" (ICLR 2025) — [ML Anthology](https://mlanthology.org/iclr/2025/zhang2025iclr-modeling/)
- Choice overload: ~3% vs ~30% purchase (24 vs 6 options); meta-analytic mean d≈0; d≈0.5–0.6 when complexity, difficulty, preference uncertainty and effort-minimization are all high — [Atticus Li](https://atticusli.com/replication-crisis/choice-overload-jam-study/)
- Schneider's "1-min BOQ ordering" is a product claim without published measurement — [Schneider Electric](https://eshop.se.com/in/blog/post/revolutionizing-b2b-industry-with-1-min-boq-ordering-on-whatsapp.html)
- Hybrid CRS hallucination rate: "22% of recommendations were not on the platform" (Granada et al., as cited in the review) — [arXiv 2508.02096](https://arxiv.org/html/2508.02096v2)
- Unilever eB2B scale figures (app, not WhatsApp): 75,000 orders/day; 500,000 retailers — [Unilever](https://www.unilever.com/news/news-search/2025/how-ai-and-ecommerce-tools-are-transforming-emerging-market-retail/)

### Inferences
- The company should define and log its own KPIs from day one: turns-to-confirmed-configuration, share of slots filled by tap vs text, abandonment per step (Flows expose per-screen completion), time from first message to PDF delivery, handoff rate, and "price/model hallucination" incidents (should be zero by construction).
- A reasonable a-priori target from the evidence: ≤6 bot turns to confirmation (5–6 slots, some batched in a Flow), 3 candidate models per turn, and explicit confirmation before any generation.

### Gaps
- No source reported completion rate or time-to-quote for a WhatsApp guided configurator in B2B; no Turkish benchmarks found.
- The Chatarmin "WhatsApp KPIs 2026" benchmark page was listed but not fetched — [Chatarmin](https://chatarmin.com/en/blog/whats-app-kpi).
