# Glossary

Terms used in this project, with Turkish equivalents.

## Drug euro (periodic euro value, *dönemsel avro değeri*)
Medicine prices in Turkey are first worked out in euros and then converted to lira. The drug euro is the exchange rate used for that conversion. It is set by the government, so it does not move every day like the market euro does. The rule is simple: take last year's average market euro (the CBRT selling rate) and multiply it by a percentage, the adaptation coefficient. When the lira loses value quickly, the market euro runs ahead of the drug euro and the gap between them grows until the next update. Since 1 April 2026 the drug euro has been 29.1164 TL. Some medicines, such as orphan drugs, biosimilars and vaccines, are priced outside this rule.

## Reference price (*kaynak fiyat*, *gerçek kaynak fiyat*)
This is the starting point of a medicine's price, and it is in euros. To find it, the Ministry of Health looks at the price of the same medicine in five EU countries (France, Spain, Italy, Portugal and Greece) and takes the lowest ex-factory price, which is the price the manufacturer charges before wholesalers and pharmacies add anything. The decree allows five to ten EU source countries, announced by a communiqué; the current list has five. Using other countries' prices to cap a price at home is called external reference pricing. The reference price only becomes a lira price in the next step.

## Wholesaler selling price (*depocuya satış fiyatı*)
This is the reference price in euros multiplied by the drug euro, so it is the first price in lira. It is the price at which the manufacturer or importer sells the medicine to the wholesaler. The wholesaler's and the pharmacist's profit margins are then added on top, and the result is the price people pay at the pharmacy. Because of this order, a drug euro that is too low pushes the whole chain down. Decree 11031 calls this price *firma satış fiyatı*, while the older Decree 10702 uses *depocuya satış fiyatı*.

## Adaptation coefficient (*uyarlama katsayısı*)
The percentage of last year's average market euro that is used as the drug euro. At 60%, a year in which the market euro averaged 100 TL gives a drug euro of 60 TL. The coefficient was 60% from February 2019 until 1 April 2026 and has been 65% since. From 2016 until February 2019 it was 70%; for earlier years it has not been verified. The dates and legal basis are in `data/manual/rule_coefficient.csv`.

Sources: Decree 11031 (Resmî Gazete, 12 March 2026), articles 2, 3 and 6, and Decree 10702 (Resmî Gazete, 19 December 2025).
