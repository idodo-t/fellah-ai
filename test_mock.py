from app.services.vision import analyze_leaf

print("=== Test variete mock ===")
resultats = {}
for i in range(10):
    r = analyze_leaf("https://test.com/photo.jpg")
    d = r["disease"]
    c = r["confidence"] * 100
    resultats[d] = resultats.get(d, 0) + 1
    print(f"  {i+1}. {d} — {c:.0f}%")

print()
print("Distribution:")
for k, v in resultats.items():
    print(f"  {k}: {v}/10")