import json

data = json.load(open('universities.json', 'r', encoding='utf-8'))
unis = data['universities']

print(f"总院校数: {len(unis)}所\n")

# 分类统计
da_xue = [u for u in unis if '大学' in u]
xue_yuan = [u for u in unis if '学院' in u and '大学' not in u]
zhi_ye = [u for u in unis if '职业' in u or '技术' in u]
qi_ta = [u for u in unis if '大学' not in u and '学院' not in u]

print(f"📊 类型分布:")
print(f"  大学类: {len(da_xue)}所")
print(f"  学院类: {len(xue_yuan)}所")
print(f"  职业/技术类: {len(zhi_ye)}所")
print(f"  其他: {len(qi_ta)}所")

print(f"\n🎓 学院类示例(前20所):")
for i, name in enumerate(xue_yuan[:20], 1):
    print(f"  {i}. {name}")

print(f"\n🔧 职业技术学院示例(前10所):")
for i, name in enumerate(zhi_ye[:10], 1):
    print(f"  {i}. {name}")

if qi_ta:
    print(f"\n📝 其他类型:")
    for name in qi_ta[:5]:
        print(f"  - {name}")
