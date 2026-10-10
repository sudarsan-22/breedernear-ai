# Photo screening accuracy

Run on 2026-10-10 with `gemini-3.8-flash`: **202/202 checks correct** across 49 photos.

Reproduce with `PYTHONPATH=. python scripts/vision_accuracy.py` (needs Google Cloud credentials). The protected result uses the app's own rule on the photo alone; in the app the seller's text is checked too, and either one is enough to block.

**Limits:** every test photo is AI-generated (sample listing photos, plus the hard cases in `data/samples/vision/`), so accuracy on real phone photos may be lower. Real photos taken with consent can be added to `cases.json`.

| Measure | Result |
|---|---|
| Protected native species blocked from the photo alone | **8/8** |
| Domestic pets wrongly flagged as protected | **0/37** |
| Domestic species named correctly | **37/37** |
| Domestic photos with no false dye flag | **37/37** |
| Domestic photos with no false stock/watermark flag | **37/37** |
| Dyed bird detected | **1/1** |
| Blurry / no-animal photo recognised | **2/2** |
| Watermarked stock photo / scam screenshot flagged | **2/2** |

## Every photo

| Photo | Set | Label | Gemini's guess (confidence) | Checks |
|---|---|---|---|---|
| LST-0001 | domestic | Budgerigar | Budgerigar (1.00) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0002 | domestic | Lovebird | Rosy-faced Lovebird (Lutino mutation) (0.98) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0003 | domestic | Cockatiel | Cockatiel (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0004 | domestic | Budgerigar | Budgerigar (Budgie) (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0005 | domestic | Labrador Retriever | Labrador Retriever puppies (0.85) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0006 | domestic | Labrador Retriever | Black Labrador Retriever puppy (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0007 | domestic | Zebra finch | Zebra finch (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0008 | domestic | Society finch | Society finch (Bengalese finch) (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0009 | domestic | Budgerigar | Budgerigar (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0010 | domestic | Lovebird | Rosy-faced lovebird (Agapornis roseicollis) (0.98) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| cockatiel-lutino-1 | domestic | Cockatiel | Lutino cockatiel (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0012 | domestic | Budgerigar | Budgerigar (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0014 | domestic | Lovebird | Rosy-faced Lovebird (albino/creamino mutation) (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0015 | domestic | Lovebird | Rosy-faced lovebird (Peach-faced lovebird) (0.98) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0016 | domestic | Fischer's lovebird | Fischer's lovebird (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0017 | domestic | Fischer's lovebird | Fischer's lovebird (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0018 | domestic | Budgerigar | Budgerigar (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0019 | domestic | Labrador Retriever | Labrador Retriever puppies (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0020 | domestic | Cockatiel | Cockatiel (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0021 | domestic | Canary | Domestic canary (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0022 | domestic | Cockatiel | Cockatiel (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0023 | domestic | Beagle | Beagle puppy (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0024 | domestic | Budgerigar | Budgerigar (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0025 | domestic | Canary | Red factor canary (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0026 | domestic | Zebra finch | Zebra finch (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0027 | domestic | Persian cat | Persian kitten (0.90) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0028 | domestic | Persian cat | Persian kitten (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0029 | domestic | Budgerigar | Budgerigar (Budgie) (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0030 | domestic | Cockatiel | Cockatiel (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0031 | domestic | Lovebird | Rosy-faced lovebird (Lutino) (0.98) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0032 | domestic | Shih Tzu | Shih Tzu puppy (0.90) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0033 | domestic | Labrador Retriever | Labrador Retriever puppy (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0034 | domestic | Beagle | Beagle puppies (0.98) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0035 | domestic | Lovebird | Rosy-faced lovebird (Agapornis roseicollis) (0.98) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0036 | domestic | Budgerigar | Budgerigar (0.98) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0039 | domestic | Budgerigar | Budgerigar (0.99) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| LST-0040 | domestic | Canary | Domestic canary (0.95) | ✅ species ✅ protected ✅ dye ✅ stock ✅ quality |
| protected-rose-ringed-adult | protected | rose ringed adult | Rose-ringed parakeet (Psittacula krameri) (0.98) | ✅ protected |
| protected-rose-ringed-chicks | protected | rose ringed chicks | Rose-ringed parakeet chicks (0.90) | ✅ protected |
| protected-alexandrine | protected | alexandrine | Alexandrine parakeet (0.95) | ✅ protected |
| protected-scaly-munia | protected | scaly munia | Scaly-breasted Munia (0.95) | ✅ protected |
| protected-red-avadavat | protected | red avadavat | Red avadavat (Amandava amandava) (0.95) | ✅ protected |
| protected-myna | protected | myna | Common Myna (0.98) | ✅ protected |
| protected-star-tortoise | protected | star tortoise | Indian star tortoise (0.98) | ✅ protected |
| protected-dyed-munia | protected | dyed munia | Indian silverbill or munia (0.85) | ✅ protected ✅ dye |
| quality-blurry | quality | blurry | Budgerigar (0.95) | ✅ protected ✅ quality |
| quality-no-animal | quality | no animal | none (0.00) | ✅ protected ✅ quality |
| stock-watermark | stock | watermark | Cockatiel (0.99) | ✅ species ✅ protected ✅ stock |
| scam-post-screenshot | stock | post screenshot | Rose-ringed Parakeet (0.95) | ✅ stock |
