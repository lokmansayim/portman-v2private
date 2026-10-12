"""SKP dosyasını çözer ve ara dosyaya yazar.  Kullanım: python kaydet.py kaynak/<ad>.skp ara/<ad>.pkl"""
import sys, pickle, skp_oku
r = skp_oku.oku(sys.argv[1])
r["p"] = {k: v for k, v in r["p"].items() if k in ("version","units","layer_colors","layer_hidden","layer_id_to_name","material_id_to_name","thumbnail_data","dimensions","pages")}
pickle.dump(r, open(sys.argv[2], "wb"))
print("ok", len(r["yuzler"]), len(r["dugumler"]))
