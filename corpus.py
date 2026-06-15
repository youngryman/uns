# 50 realistic headlines. Each tagged with ground truth:
#   'good'  = should produce a valid split
#   'noverb'= legitimately has no verb -> correct discard
# This lets us classify every discard as GENUINE or FALSE.
CORPUS = [
 ("Scientists discover new species in Amazon rainforest", "good"),
 ("Senate approves sweeping budget plan after late vote", "good"),
 ("Mayor unveils plan to reduce traffic congestion", "good"),
 ("Police report shows sharp decline in downtown crime", "noverb"),  # 'report' noun
 ("Officials report a surge in seasonal flu cases", "good"),
 ("Tech giant announces breakthrough in battery research", "good"),
 ("Floods force thousands to flee coastal villages", "good"),
 ("President signs trade deal with neighboring nations", "good"),
 ("Study warns of accelerating ice loss in Antarctica", "good"),
 ("Wildfire threatens homes across drought-stricken region", "good"),
 ("Court rejects appeal in long-running fraud case", "good"),
 ("Stocks plunge as inflation fears grip markets", "good"),
 ("Airline cancels hundreds of flights amid staff shortage", "good"),
 ("Doctors warn against new social media health trend", "good"),
 ("Voters head to polls in tightly contested election", "good"),
 ("Company recalls product over safety concerns", "good"),
 ("Researchers develop test for early cancer detection", "good"),
 ("Storm knocks out power to millions overnight", "good"),
 ("Government cuts funding for rural transport links", "good"),  # 'cuts' verb / 'funding'
 ("Activists demand action on plastic pollution", "good"),
 ("Hackers breach database of major retailer", "good"),
 ("City council debates ban on gas-powered leaf blowers", "good"),
 ("Farmers protest rising fuel and fertilizer costs", "good"),
 ("Star striker signs record contract with rival club", "good"),
 ("Volunteers rescue stranded whales from beach", "good"),
 ("Budget talks collapse as parties trade blame", "noverb"),  # 'talks' noun, 'collapse' after
 ("Peace talks resume after months of deadlock", "noverb"),   # 'talks' noun
 ("Aid groups warn of famine in conflict zone", "good"),
 ("Border crossing reopens after lengthy closure", "good"),
 ("Tourists flock to newly opened mountain trail", "good"),
 ("Regulators probe airline over hidden fees", "good"),
 ("Heatwave breaks century-old temperature records", "good"),
 ("Union calls strike over stalled wage talks", "noverb"),  # 'calls' verb but 'strike' object then ok? test
 ("Lawmakers push bill to expand rural broadband", "good"),
 ("Drought devastates crops across the plains", "good"),
 ("Museum returns looted artifacts to home country", "good"),
 ("Startup raises millions for clean energy venture", "good"),
 ("Protesters march against proposed pension reforms", "good"),
 ("Hospital opens new wing for pediatric care", "good"),
 ("Quake rattles remote islands but spares cities", "good"),
 ("Breaking news shocks investors across Asia", "good"),  # verb-first-ish
 ("Champion retains title in thrilling final", "good"),
 ("Critics slam decision to close historic theater", "good"),
 ("Engineers test prototype for hydrogen-powered train", "good"),
 ("Smoke blankets city as fires rage nearby", "good"),
 ("New report details failures in flood response", "noverb"),  # 'report' noun, 'details' verb after
 ("Whistleblower exposes corruption at city hall", "good"),
 ("Refugees cross border seeking safety and shelter", "good"),
 ("Festival draws record crowds despite rain", "good"),
 ("Surgeons perform first robotic heart transplant", "good"),
]
