# M5 judge calibration: blind labeling sheet

Score each of the 20 answers 1-5 against its reference with the rubric below, without looking at the judge's scores. Enter each score as `student_score` in `evals/results/judge_calibration_blind.jsonl` (same keys).

```
You grade an answer to a question about a company's SEC filings against a reference
answer written by an analyst. Score 1-5:
5: covers all key points of the reference; nothing contradicted or invented.
4: covers most key points; minor omissions only.
3: covers about half of the key points, or makes one material error.
2: covers few key points, or materially contradicts the reference.
1: wrong, invented, or off-topic.
```

## 1. `71ed8e0b0cffc60358f2b0204c895582`

**Question:** How exposed is Amazon to swings in currency exchange rates?

**Reference:** Amazon is meaningfully exposed: International was 22% of 2024 sales (mostly euros, pounds and yen), and currency moves cut International sales by $1.8 billion versus 2023. A 10% adverse move would reduce its $25.5 billion of foreign funds by $2.6 billion and cause $605 million of intercompany remeasurement losses.

**Answer:**

> Amazon has meaningful but not dominant exposure to currency swings. In its 10-K, it says International segment sales were roughly 21-23% of consolidated net sales in recent years. Those sales, and the related expenses, are mostly denominated in euros, British pounds, and Japanese yen. Canada and Mexico, which are reported within North America, add some exposure, and AWS and certain intercompany balances are also exposed.
>
> Exchange rates affect Amazon in two main ways:
>
> - **Translation:** A stronger dollar lowers reported International revenue and operating results when they are converted into dollars. Amazon regularly cites FX as a swing factor in its results, for example a multibillion-dollar headwind in 2022.
> - **Remeasurement:** Intercompany balances can produce gains or losses.
>
> Because costs are largely incurred in the same local currencies as revenue, the effect on operating income is partly offset. Amazon also uses some foreign currency hedges, though it has not described them as eliminating the risk. I'm recalling these figures from memory, so check the latest 10-K's Item 7A and the segment discussion for exact percentages and dollar impacts.

**Your score (1-5):** ___

## 2. `5a58fd86071d96edb0db2effc5752860`

**Question:** Why did Nike's sales fall in fiscal 2025?

**Reference:** Nike's fiscal 2025 revenues fell 10% to $46.3 billion because of lower traffic across NIKE Direct and deliberate actions to reduce the supply of certain footwear through heavier markdowns, wholesale discounts and higher returns; revenues declined in North America, EMEA and Greater China, footwear unit sales fell 8% with lower prices from discounts, and NIKE Direct fell 12% currency-neutral as digital sales dropped 20%.

**Answer:**

> Nike's fiscal 2025 revenues (year ended May 31, 2025) were about $46.3 billion, down roughly 10% from the prior year. As I recall from its filings, the decline had several causes:
>
> - **Weaker demand in key franchises:** Sales of long-running lifestyle franchises such as Air Force 1, Dunk, and Air Jordan 1 fell as Nike deliberately cut back supply, and new products had not yet fully replaced them.
> - **Lower Nike Direct sales:** Nike's own digital and store sales fell by double digits, and the company pulled back on some promotional activity and digital marketing.
> - **Lower wholesale sales:** Sales to retail partners also declined, though by less than Nike Direct.
> - **Greater China:** Revenue there fell notably amid a weaker consumer environment.
> - **Converse:** Converse revenue fell sharply.
> - **Currency:** Unfavorable foreign exchange added a small additional drag.
>
> Management framed this as part of a transition to a sport-focused strategy and a reset of its product mix and channel relationships. I'm confident about the overall decline and its main drivers, but I'm less sure of the exact segment and regional figures, so check the 10-K for precise numbers.

**Your score (1-5):** ___

## 3. `8d215a33376e0fc47625e4375b39e9fb`

**Question:** Why does JPMorgan Chase say it cannot guarantee absolute security against cyberattacks?

**Reference:** JPMorgan says it cannot always anticipate or detect threats because attack techniques evolve quickly and may go unnoticed for long periods, attacks come from many sources (insiders, criminals, hacktivists, hostile nation-states), it doesn't control the security of its many clients and vendors, and an undetected intruder could move from one network to others. It states that past breaches have occurred and future ones are inevitable.

**Answer:**

> JPMorgan Chase's 10-K risk factors say it cannot guarantee absolute security because cyber threats are persistent, evolving, and partly outside its control. As I recall the filing's language, the main reasons are:
>
> - **Attack methods change constantly.** Techniques are increasingly sophisticated, often aren't recognized until launched, and can come from nation-states, organized crime, hackers, and "hacktivists." New technologies such as AI add to the risk.
> - **Third parties and interconnections.** The firm depends on vendors, service providers, exchanges, clearinghouses, and other financial institutions. It can't fully control their security, and a breach at one of them could affect JPMorgan.
> - **Scale and complexity.** The firm handles a very large volume of transactions, customers, and data across many systems, which creates many possible points of attack.
> - **Human and operational factors.** Employee error or misconduct, phishing, and social engineering can bypass technical safeguards.
>
> The firm says it invests heavily in controls, monitoring, and incident response, but those measures may not prevent or quickly detect every attack, and a successful one could cause financial loss, legal and regulatory consequences, and reputational harm.
>
> I'm summarizing from memory rather than quoting the filing, so check the latest 10-K's "Risk Factors" and "Cybersecurity" sections for the exact wording.

**Your score (1-5):** ___

## 4. `91e41b09d63550ed87798d69a9e92850`

**Question:** Why did NVIDIA write off billions in chip inventory in early fiscal 2026?

**Reference:** On April 9, 2025, the U.S. government required a license to export NVIDIA's H20 chips to China. Demand for H20 collapsed, so NVIDIA took a $4.5 billion charge in Q1 fiscal 2026 for H20 excess inventory and purchase obligations, which cut gross margin.

**Answer:**

> NVIDIA said the charge followed a new U.S. government license requirement for H20 exports to China. Demand for H20 products then diminished, leaving excess inventory and purchase obligations. NVIDIA recorded a $4.5 billion charge in Q1 FY2026 (quarter ended April 27, 2025). Total Q1 inventory provisions were $5.3 billion, and the net effect on gross margin was an unfavorable 11.0%. Gross margin was 60.5% in Q1, against 73.0% in the prior quarter (derived Q4 FY2025). In Q2 FY2026, margin recovered to 72.4%. NVIDIA sold about $650 million of H20 to a customer outside China and released $180 million of the reserved inventory. The filings call this a "charge" or "provision", not a write-off.
> NVIDIA said that on April 9, 2025 the U.S. government informed it that a license is required to export H20 products to China (including Hong Kong and Macau) and D:5 countries. As a result, it incurred a $4.5 billion charge in Q1 FY2026 for H20 excess inventory and purchase obligations "as the demand for H20 products diminished."
> NVIDIA said the $4.5 billion charge was less than it initially anticipated because it was able to re-use certain materials.
> NVIDIA's risk factors say that export controls restricting sales of a product can result in excess inventory and purchase obligations, "as we recently experienced with the H20." They also say reduced demand due to export controls "has and could in the future lead to excess inventory or cause us to incur related supply charges."
> NVIDIA reported that provisions for inventory and excess inventory purchase obligations totaled $5.3 billion in Q1 FY2026, including the $4.5 billion for H20, against $393 million in Q1 FY2025. The net effect on gross margin was an unfavorable 11.0%, against 1.1% a year earlier.
> NVIDIA said Q1 gross margin fell to 60.5% from 78.4% a year earlier. It attributed the fall primarily to the $4.5 billion H20 charge and to the initial ramp of more sophisticated Data Center systems. It also said H20 sales were $4.6 billion in Q1 before the new export licensing requirements, and that the requirements have affected current revenue and will negatively affect future revenue.
> Computed gross margin (gross profit divided by revenue) was about 73.0% in Q4 FY2025, the baseline quarter (derived from annual less nine-month figures).
> Computed gross margin was about 60.5% in Q1 FY2026, the quarter of the H20 charge.
> Gross margin fell about 12.5 percentage points from Q4 FY2025 to Q1 FY2026.
> Computed gross margin recovered to about 72.4% in Q2 FY2026.
> In Q2 FY2026, NVIDIA recognized about $650 million of H20 revenue from sales to an unrestricted customer outside China. This resulted in a $180 million release of previously reserved H20 inventory. The net effect of provisions on gross margin was an unfavorable 1.1% in Q2 and 5.9% in the first half. NVIDIA also said first-half gross margin was affected by the $4.5 billion H20 charge.

**Your score (1-5):** ___

## 5. `54b1195ec79868b1bbf8dbd19ecac2e8`

**Question:** How does Microsoft describe its Copilot and AI offerings in its business overview?

**Reference:** Microsoft describes itself as entering a new age of AI, with Copilot and its Copilot stack driving AI transformation: Copilot for Microsoft 365 and role-based Copilots, Copilot Studio and Copilot Pro, GitHub Copilot, Copilot in Bing, Edge and Copilot+ PCs, plus the Azure AI platform, the OpenAI partnership, and custom AI infrastructure.

**Answer:**

> In Item 1 of its FY2026 10-K, Microsoft presents AI as central to its business. It says its AI offerings span every layer of the technology stack. It names Microsoft 365 Copilot and agents as the way it applies AI to productivity. It describes Microsoft 365 Commercial as an AI-powered platform that includes Microsoft 365 Copilot. It describes Azure AI offerings and Azure AI Foundry as the platform for building AI applications and agents.
> Microsoft's general overview says AI is "fundamentally transforming productivity for every individual, organization, and industry" and that its AI offerings "span every layer of the technology stack."
> In its strategy, Microsoft describes applying AI and ambient intelligence to drive insights, revolutionize many types of work and business processes, and provide substantive productivity gains using Microsoft 365 Copilot and agents. It also describes providing a unified intelligence layer for enterprise AI to ground AI in an organization's data.
> Microsoft describes Microsoft 365 Commercial as an AI-powered business and productivity solutions platform that brings together Office, Windows, Microsoft 365 Copilot, and Enterprise Mobility + Security to help organizations empower their employees.
> In the Azure section, Microsoft says Azure AI offerings provide a competitive advantage as companies seek ways to optimize and scale their business with AI. It describes Azure AI Foundry as a unified platform for developers to design, customize, and manage AI applications and agents.

**Your score (1-5):** ___

## 6. `a9d15407ccf6684df72bade365ee23ed`

**Question:** How does Coca-Cola price the concentrate it sells to its bottlers?

**Reference:** Coca-Cola's bottler's agreements generally give it flexibility to set concentrate prices, though competitive market conditions limit this in practice; in most markets it uses an incidence-based pricing model where the concentrate price depends on factors such as bottler pricing, sales channels and package mix, while remaining U.S. legacy agreements use a baseline price adjustable up to an indexed ceiling and adjusted quarterly for sweetener costs.

**Answer:**

> Coca-Cola's 10-K says that, under its bottling agreements, the company generally has the right to set the prices it charges bottlers for concentrates, and it can change them at its discretion. In many markets, including the U.S., concentrate pricing follows an "incidence-based" model. Under it, the price depends on factors such as the product, package type, and sales channel, and it is tied to the price of the finished beverage sold by the bottler. Concentrate revenue therefore tends to move with bottlers' finished-product pricing and mix. The company also sells syrups to fountain customers and wholesalers, which are priced differently. I'm working from memory of the filings' general language, so for exact terms, which vary by territory and agreement, check the latest 10-K's sections on bottling agreements and revenue recognition.

**Your score (1-5):** ___

## 7. `f559dab7145675c8769dc8bd6dba028b`

**Question:** Why did Tesla make less profit on its cars in 2024?

**Reference:** Tesla's automotive gross margin fell from 19.4% to 18.4% in 2024 mainly because price cuts and attractive financing offers lowered its average selling price, and the costly Cybertruck ramp added pressure. Lower per-unit costs (raw materials, freight) and higher regulatory credit and FSD revenue partly offset the decline.

**Answer:**

> Tesla's 2024 10-K attributes the lower automotive profit mainly to lower prices. Automotive sales revenue fell roughly 8%, even though deliveries were nearly flat at about 1.79 million vehicles. The company cited price cuts, incentives, and financing offers, plus a shift toward lower-priced vehicle variants, which cut the average selling price. Per-unit costs also fell, but not by enough to offset the lower prices, and costs tied to ramping the Cybertruck and other new products weighed on margins. Growing regulatory credit revenue and some cost reductions partly offset this. Tesla also took restructuring charges in 2024 and spent more on AI and other development, which hurt overall profit beyond vehicle margins. I'm confident about the general drivers but not certain of the exact figures, so check the MD&A section of the 10-K for precise numbers.

**Your score (1-5):** ___

## 8. `a086f1c34f4725aa6455f030a092acf4`

**Question:** How much did eCommerce contribute to Walmart U.S. comparable sales in fiscal 2025?

**Reference:** Walmart U.S. eCommerce sales contributed approximately 2.9% to the segment's 4.8% comparable sales growth in fiscal 2025 (up from 2.6% in fiscal 2024), driven primarily by store-fulfilled pickup and delivery.

**Answer:**

> Walmart's 10-K says eCommerce added approximately 2.9% to Walmart U.S. comparable sales in fiscal 2025. That compares with approximately 2.6% in fiscal 2024. Walmart U.S. comparable sales rose 4.8% in fiscal 2025.
> Walmart reported that Walmart U.S. eCommerce sales positively contributed approximately 2.9% to comparable sales in fiscal 2025, up from approximately 2.6% in fiscal 2024.
> Walmart U.S. comparable sales increased 4.8% in fiscal 2025 (5.5% in fiscal 2024), so the 2.9% eCommerce contribution is measured against that total.
> Walmart said the eCommerce contribution was primarily driven by store-fulfilled pickup and delivery.

**Your score (1-5):** ___

## 9. `23d80aee072a8919500986595846106b`

**Question:** What does Apple's value-at-risk model estimate for its foreign currency exposure?

**Reference:** Apple's Monte Carlo VaR model estimates, with 95% confidence, a maximum one-day loss in fair value on its foreign currency derivatives of $538 million as of September 28, 2024, versus $669 million as of September 30, 2023.

**Answer:**

> I'm not certain of the exact figures. As I recall, Apple's older 10-Ks (roughly through the late 2010s) described a value-at-risk (VAR) model in the market risk section. It estimated the potential one-day loss in fair value of its foreign currency derivatives and other market-risk-sensitive instruments, using a statistical confidence level (I believe 95%). Apple reported the resulting VAR as a dollar amount, which was small relative to its total financial position.
>
> In more recent filings, I believe Apple moved away from VAR. It now uses a sensitivity analysis instead, which shows the change in fair value of its foreign currency derivatives from a hypothetical 10% adverse move in exchange rates against the U.S. dollar. I can't confirm the exact year of the change or the dollar amounts, so check Item 7A of the specific 10-K you're interested in.

**Your score (1-5):** ___

## 10. `ca80c1c3a9f920e0a484e9abf0bc1f16`

**Question:** How does Coke protect itself against currency and commodity price swings?

**Reference:** Coca-Cola uses derivatives only to hedge, not for trading: it manages most currency exposure on a consolidated basis to net exposures and capture natural offsets, then hedges with forward contracts, currency options and collars (mainly euro, British pound and Japanese yen), and it manages commodity risk on inputs like sweeteners, metals, juices, PET and fuels mainly through supplier pricing agreements that fix purchase prices, adding commodity derivatives when appropriate.

**Answer:**

> Coca-Cola says it uses derivatives, not speculation, to manage these risks, according to its 10-K. For currency, it uses forward contracts, options, collars, and swaps to hedge forecasted transactions like foreign-currency sales and purchases of inventory. These are generally designated as cash flow hedges. It also hedges the value of some net investments in foreign subsidiaries, using derivatives and foreign-currency-denominated debt, and it uses fair value hedges and swaps to manage interest rate and debt-related currency exposure. For commodities, the company says it uses derivatives to hedge some of its exposure to the prices of sweeteners, metals (aluminum), juices, PET plastic, and energy. Beyond derivatives, it relies on natural hedges from operating in many currencies and on pricing actions. It also manages counterparty risk by dealing with highly rated institutions and using netting agreements. The company cautions that these hedges are not complete, so large currency or input-cost swings can still hurt results. For specific notional amounts, hedge durations, or current positions, check the market risk and derivatives notes in the latest 10-K, as I'm not certain of the current figures.

**Your score (1-5):** ___

## 11. `84975b16b6b9daeed1a72190e5ca58b6`

**Question:** How could Meta's heavy spending on virtual and augmented reality go wrong?

**Reference:** Meta warns that the metaverse may not develop as expected, demand for its VR/AR products is uncertain, it has limited hardware experience, and new regulation could slow it down. The spending also diverts resources and has produced little revenue: Reality Labs cut 2024 operating profit by about $17.73 billion, with larger losses expected in 2025, and the investments may never succeed.

**Answer:**

> Meta's 10-K filings describe several ways this could go wrong. The main one is that the spending may never pay off. Reality Labs has lost roughly $13-18 billion a year recently (about $17-18 billion in 2024, from my recollection, so check the filing), on only a couple of billion dollars of revenue, and Meta has said it expects these losses to keep growing. If consumers and developers don't adopt VR/AR headsets, smart glasses, and the metaverse as hoped, Meta could absorb tens of billions in cumulative losses with little return. The filings also flag other risks:
>
> - **Hardware challenges:** Products are costly to build, and Meta depends on supply chains and key component suppliers.
> - **Competition:** Apple, Google, and others are pursuing the same market.
> - **Regulation:** Privacy, safety, and content rules for immersive and wearable devices are uncertain.
> - **Dependence on third-party platforms:** Meta's reliance on others' mobile ecosystems could limit its reach until it controls its own computing platform.
> - **Opportunity cost:** The spending could squeeze profits or divert capital and attention from the core advertising business and from AI investment.
>
> Meta also acknowledges that these long-term bets may not be profitable on the timelines investors expect.

**Your score (1-5):** ___

## 12. `a7b96b39deeec61e90819198dc10f906`

**Question:** What risks does Johnson & Johnson describe from Medicare drug price negotiation under the Inflation Reduction Act?

**Reference:** Johnson & Johnson says the Inflation Reduction Act changed Medicare Part D's benefit design and subjected some of its products to government-set prices starting in 2026, with more products possibly selected later. It also warns that not following the government's interpretation of the law while litigation is pending could bring penalties, and that the Part D changes could hurt U.S. Innovative Medicine sales.

**Answer:**

> In its FY2025 10-K risk factors, Johnson & Johnson says the Inflation Reduction Act of 2022 has changed Medicare Part D benefit design. It also says the Act has subjected certain of its products to government-established pricing beginning in 2026, and that more products may be subject in the future. J&J warns that failing to follow the government's interpretations of the law while litigation is pending could expose it to penalties. It also says Medicare Part D changes could hurt U.S. Innovative Medicine sales. The disclosure is qualitative, with no quantified impact. The FY2026 Q2 10-Q has no Item 1A of its own.
> Johnson & Johnson states that the Inflation Reduction Act of 2022 (IRA) has changed Medicare Part D benefit design and has subjected certain of the Company's products to government-established pricing beginning in 2026. It adds that the IRA may subject additional products in the future.
> J&J warns that failure to adhere to the government's interpretations of the law pending ongoing litigation may expose the Company to penalties.
> J&J says that change to Medicare Part D could have a negative impact on U.S. Innovative Medicine sales.

**Your score (1-5):** ___

## 13. `e7eb2cfcbdc1f5701d05d4ea71ff2050`

**Question:** What savings does Pfizer expect from its Cost Realignment Program?

**Reference:** Pfizer expects its Realigning Our Cost Base Program (the cost realignment program launched in Q4 2023) to deliver total net cost savings of about $4.5 billion by the end of 2025, and says most of those savings were already achieved by year-end 2024.

**Answer:**

> The filings don't use the name "Cost Realignment Program". The closest match is the "Realigning Our Cost Base Program", which I've treated as the same program. In the FY2025 10-K, Pfizer expected total net cost savings of approximately $5.7 billion through 2026. The Q2 2026 10-Q raises that to approximately $6.7 billion through 2029, after $1.0 billion of additional anticipated savings. The additional savings carry about $2.0 billion of one-time costs.
> In its FY2025 10-K, Pfizer said the Realigning Our Cost Base Program was expected to deliver total net cost savings of approximately $5.7 billion through 2026. Of that, $5.1 billion had been achieved through 2025. The remaining $600 million, primarily in SI&A, was expected by the end of 2026.
> In its Q2 2026 10-Q, Pfizer said it announced $1.0 billion of additional anticipated net cost savings for the program. It said it now expects total net cost savings of approximately $6.7 billion through 2029, compared with the previously announced approximately $5.7 billion through 2026.
> Pfizer said the additional net savings are expected to further reduce SI&A costs and be realized from 2027 through 2029. It expects one-time costs to achieve them, incurred through 2029, to total approximately $2.0 billion.

**Your score (1-5):** ___

## 14. `68e09165f21b845803a07671e6db2c69`

**Question:** Why does JPMorgan Chase say it cannot guarantee absolute security against cyberattacks?

**Reference:** JPMorgan says it cannot always anticipate or detect threats because attack techniques evolve quickly and may go unnoticed for long periods, attacks come from many sources (insiders, criminals, hacktivists, hostile nation-states), it doesn't control the security of its many clients and vendors, and an undetected intruder could move from one network to others. It states that past breaches have occurred and future ones are inevitable.

**Answer:**

> JPMorgan Chase does not use the exact phrase "absolute security" in the retrieved FY2025 10-K risk factors. It says it cannot guarantee that it will always detect cybersecurity threats or implement effective preventive measures against them. Its stated reasons are that attack techniques evolve and grow more sophisticated, so attacks may go undetected for long periods, and that it does not control the cybersecurity of the clients, customers, counterparties and third-party providers it does business with. It also says it experiences numerous cyber attacks and could become more vulnerable if it fails to address emerging threats and known vulnerabilities in time.
> The retrieved risk factor text does not use the exact phrase "absolute security". The closest language is that JPMorganChase "cannot guarantee that it will always detect cybersecurity threats to its systems or implement effective preventive measures against those threats."
> JPMorgan gives as one reason that the techniques used in cyber attacks evolve frequently and increase in sophistication. As a result, an attack may not be recognized until launched or may go undetected for extended periods.
> JPMorgan says it does not have control over the cybersecurity of the systems of the numerous clients, customers, counterparties and third-party service providers with which it does business.
> JPMorgan says it could become increasingly vulnerable to cyber attacks if it does not, in a timely manner, identify and address emerging threats, known vulnerabilities or shortcomings in its cybersecurity controls. These include zero-day vulnerabilities, meaning unknown security flaws in software and hardware.
> JPMorgan states that it experiences numerous cyber attacks on its computer systems, software, networks and other technology assets.

**Your score (1-5):** ___

## 15. `0494d6a9ba316652dda1819e4ee67a73`

**Question:** How did Disney explain the improvement in Direct-to-Consumer operating income in fiscal 2024?

**Reference:** Disney said Direct-to-Consumer operating results improved by $2,639 million in fiscal 2024, from an operating loss of $2,496 million to operating income of $143 million, due to improved results at Disney+, where programming costs fell on lower non-sports content costs, partially offset by higher Hulu Live TV programming fees and higher marketing and labor costs.

**Answer:**

> Disney said Direct-to-Consumer operating results rose $2,639 million, to operating income of $143 million from an operating loss of $2,496 million, "due to improved results at Disney+." The supporting detail is higher subscription and advertising revenue and lower Disney+ programming costs. These were partly offset by higher cricket programming costs and higher marketing and labor costs.
> Disney's FY2024 10-K MD&A says Direct-to-Consumer operating results increased $2,639 million, to operating income of $143 million from an operating loss of $2,496 million, due to improved results at Disney+.
> On revenue, Disney said subscription fee growth reflected a 10% increase from higher effective rates due to retail pricing increases and 6% from subscriber growth, partly offset by a 2% decrease from an unfavorable foreign exchange impact. Higher advertising revenue reflected a 26% increase from higher impressions, partly offset by a 12% decrease from lower rates.
> On costs, Disney attributed the decrease in programming and production costs at Disney+ and other to lower costs for non-sports content on Disney+, partly offset by higher cricket programming costs at Disney+ Hotstar. Selling, general, administrative and other costs rose $406 million, to $4,574 million from $4,168 million, mainly on higher marketing and labor costs.
> The DTC results table shows total revenues of 22,776 versus 19,886 (up 15%) and operating expenses of 17,748 versus 17,859 (a 1% change shown as favorable). This is the revenue growth alongside slightly lower operating expenses behind the improvement.

**Your score (1-5):** ___

## 16. `53d36f6694ca166180cd01c0c17c318a`

**Question:** What restructuring plan did P&G announce in fiscal 2025, and why did it start it?

**Reference:** In June 2025, P&G announced a two-year portfolio and productivity plan to streamline its portfolio and organization and improve its cost structure and competitiveness, expecting about $1.5 to $2.0 billion in before-tax restructuring costs (including its ongoing plan) and a reduction of up to 7,000 non-manufacturing overhead roles by the end of fiscal 2027.

**Answer:**

> In June 2025, P&G announced a portfolio and productivity plan. The filing says the plan's purpose is to streamline the company's portfolio and organization to improve its cost structure and competitiveness. P&G expects about $1.5 to $2.0 billion of before-tax restructuring costs over two years. That figure includes the ongoing plan. The plan includes a reduction of up to 7,000 non-manufacturing overhead personnel by the end of fiscal 2027. The passages give only this general rationale and no more specific reason.
> In June 2025, P&G announced a portfolio and productivity plan (the passages' notes call it the 'Focused Portfolio, Supply Chain and Productivity Plan'). The company said it was to streamline its portfolio and organization to improve its cost structure and competitiveness.
> P&G expects approximately $1.5 to $2.0 billion in before-tax restructuring costs over a two-year period, including costs from this plan and the ongoing plan. The restructuring activities include a plan to reduce up to 7,000 non-manufacturing overhead personnel by the end of fiscal 2027.
> Separately, P&G's earlier limited market portfolio restructuring, which the company started in fiscal 2024, was primarily in certain Enterprise Markets, including Argentina and Nigeria. P&G said it was meant to address challenging macroeconomic and fiscal conditions. This is not the June 2025 plan.
> In fiscal 2025, P&G incurred before-tax restructuring costs of $1.1 billion. These include a non-cash charge of $752 million for accumulated foreign currency translation losses due to the substantial liquidation of operations in Argentina.

**Your score (1-5):** ___

## 17. `867d3a803fa8acd10539904b7a3d252d`

**Question:** How did buying Pioneer change Exxon's oil and gas production in 2024?

**Reference:** After the Pioneer deal closed on May 3, 2024, ExxonMobil's Q2 2024 production rose 750 thousand oil-equivalent barrels per day from a year earlier to 4.4 million, which Exxon attributed to the Pioneer acquisition together with record output in Guyana and its heritage Permian assets. The filing does not break out Pioneer's contribution separately.

**Answer:**

> Buying Pioneer (closed May 2024) was one of the biggest drivers of Exxon's higher 2024 output. As I recall from the filings, Exxon's oil-equivalent production rose to about 4.3 million barrels per day in 2024, from about 3.7 million in 2023. Pioneer's Permian Basin assets added roughly half a million barrels per day for the part of the year Exxon owned them, and Permian output exceeded 1.5 million barrels per day by late 2024. Growth in Guyana also contributed meaningfully, while divestments and normal field declines offset some of the gains. I'm working from memory of the figures, so please check the exact numbers, especially Pioneer's specific contribution, against Exxon's 2024 10-K.

**Your score (1-5):** ___

## 18. `03b5618e11a82cbd1a497d9016f02656`

**Question:** Why were UnitedHealth's medical costs higher than expected in 2025?

**Reference:** UnitedHealth said 2025 medical costs ran above expectations because care activity, especially physician and outpatient visits, rose more than its pricing assumed, unit costs and service intensity increased with provider pricing, and its member mix got costlier (new value-based care patients, Medicare Advantage members from exiting plans, and sicker individual exchange members). The IRA's Part D changes also shifted more cost risk onto plans.

**Answer:**

> UnitedHealth said the overshoot came mainly from higher-than-expected care utilization, especially in Medicare Advantage, where seniors used more outpatient and physician services and some hospital care than the company had priced for. It also pointed to cost pressure in Medicaid, where the mix of members and their health needs shifted, and to weakness in some Optum Health value-based care arrangements. Its 2025 pricing and benefit designs hadn't anticipated these trends, so its medical care ratio rose sharply (to roughly 89% in Q2 from the mid-80s a year earlier). That led it to suspend and later reset its guidance, and it said it would raise prices, cut benefits and exit unprofitable plans for 2026. I'm working from memory of the earnings disclosures, so the exact figures and the weight of each factor should be checked against the 2025 10-Qs and the 10-K.

**Your score (1-5):** ___

## 19. `03c205ac5d19db4f5b88f4bd4bfe7ff7`

**Question:** As of its fiscal 2024 10-K, what was the status of Chevron's Hess acquisition and the Stabroek arbitration?

**Reference:** As of its fiscal 2024 10-K, Chevron's Hess acquisition was still pending: the FTC had cleared it with a consent agreement on September 30, 2024, but closing depended on the arbitration over Exxon and CNOOC's right of first refusal in the Stabroek Block. The merits hearing was set for May 2025 with a decision expected about three months later, and the merger would not close unless the right of first refusal was found inapplicable or the parties otherwise resolved it.

**Answer:**

> In Chevron's FY2024 10-K, the Hess acquisition had not closed. Hess stockholders had approved the merger on May 28, 2024. The Stabroek right-of-first-refusal arbitration was unresolved and had delayed completion. The merits hearing was scheduled for May 2025, with a decision expected about three months later. An adverse decision would cause the transaction not to be completed. The filing gave no closing date.
> The Hess merger was still pending as of the FY2024 10-K. Chevron said the Stabroek right-of-first-refusal arbitration, among Hess Guyana Exploration Limited, affiliates of Exxon Mobil, and CNOOC, had delayed completion of the transaction. Chevron said neither it nor Hess could predict the actual completion date, if at all.
> Hess stockholder approval was obtained: on May 28, 2024, a majority of Hess stockholders voted to approve the merger.
> The Stabroek arbitration was ongoing. The merits hearing was scheduled for May 2025, with a decision expected in approximately the following three months. The 10-K reports no decision.
> Chevron warned that if the arbitration does not confirm the Stabroek ROFR is inapplicable to the merger, and the parties do not otherwise agree on an acceptable resolution, a closing condition would fail and the merger would not close. An arbitration decision against Hess Guyana would cause the transaction not to be completed.
> Chevron and Hess said they would continue to take steps to maintain their ability under the Hart-Scott-Rodino Act to close the merger following satisfactory resolution of the ongoing arbitration proceedings. The Guyana approval condition had not been triggered as of the filing date. The FTC had issued a Second Request on December 7, 2023.

**Your score (1-5):** ___

## 20. `1402e208e57b50ee8854d0ec5e0291a3`

**Question:** How did Alphabet explain the increase in capital expenditures for technical infrastructure in 2024?

**Reference:** Alphabet's capital expenditures rose from $32.3 billion in 2023 to $52.5 billion in 2024, driven primarily by investments in technical infrastructure (servers, network equipment, and data centers), including to support AI. It expected to increase this investment further.

**Answer:**

> Alphabet's capital expenditures were $32.25 billion in FY2023. Alphabet's capital expenditures were $52.5 billion in FY2024. Capital expenditures grew about 62.9% from FY2023 to FY2024. The dollar increase in capital expenditures was about $20.3 billion. Alphabet attributed the increase in purchases of property and equipment primarily to investments in technical infrastructure. It said it invests in land, buildings, and servers and network equipment, through purchases and lease arrangements, to provide capacity for the growth of its services and products. Alphabet said it expects to increase its investment in technical infrastructure, including servers, network equipment, and data centers, relative to 2024. It said this is to support the growth of its business and its long-term initiatives, in particular in support of AI products and services. It also said it will invest heavily in operating and capital expenditures as it continues to serve users and expand its businesses.
> Alphabet's capital expenditures were $32.25 billion in FY2023.
> Alphabet's capital expenditures were $52.5 billion in FY2024.
> Capital expenditures grew about 62.9% from FY2023 to FY2024.
> The dollar increase in capital expenditures was about $20.3 billion.
> Alphabet attributed the increase in purchases of property and equipment primarily to investments in technical infrastructure. It said it invests in land, buildings, and servers and network equipment, through purchases and lease arrangements, to provide capacity for the growth of its services and products.
> Alphabet said it expects to increase its investment in technical infrastructure, including servers, network equipment, and data centers, relative to 2024. It said this is to support the growth of its business and its long-term initiatives, in particular in support of AI products and services. It also said it will invest heavily in operating and capital expenditures as it continues to serve users and expand its businesses.

**Your score (1-5):** ___
