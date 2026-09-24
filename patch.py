#!/usr/bin/env python3
# Copyright (c) 2026 Timo Heimonen
# SPDX-License-Identifier: MIT

"""Patch an original Street Rod 2 Disk 1 ADF for KS3.1/AGA/MC68060.

This file is intentionally self-contained and uses only the Python standard
library.  It verifies the complete source and result images, edits the Amiga
Old File System directly, and never writes to the source ADF.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import struct
import sys
import tempfile
import zlib


VERSION = "1.8.1"

BLOCK_SIZE = 512
BLOCK_LONGS = BLOCK_SIZE // 4
ADF_BLOCKS = 1760
ADF_SIZE = BLOCK_SIZE * ADF_BLOCKS
ROOT_BLOCK = 880
RESERVED_BLOCKS = 2
OFS_DATA_SIZE = BLOCK_SIZE - 24
HASH_SIZE = BLOCK_LONGS - 56
POINTERS_PER_BLOCK = BLOCK_LONGS - 56

T_HEADER = 2
T_DATA = 8
T_LIST = 16
ST_ROOT = 1
ST_USERDIR = 2
ST_FILE = 0xFFFFFFFD

SOURCE_ADF_SHA256 = (
    "4444796c1c9337baf16dffa982f1e66dc579a04d3e80a8ffa6a483b648e7bb1c"
)
PATCHED_ADF_SHA256 = (
    "2ffd2d717023f99307451394b0a75d94601aa8a9e77924d18a01a12c0c0cde60"
)
SOURCE_PROGRAM_SHA256 = (
    "a345fb91144d1ee577dcd5c80a8a8aa3b0a4e777ed9b5b4308d3a2b36d8df3a8"
)
PATCHED_PROGRAM_SHA256 = (
    "1aa7d7c8d44cb7f9bb2048431deef5d56803f794e82239cb25bd2903ffd51463"
)
TRAINER_SHA256 = (
    "648dbe599570549aea8dd7793d4d405db7f81eb96793e45e52dc22bc575f8e92"
)


PACKED_PROGRAM_SHA256 = "34d1ec3b0fcabb41eadd5dee22a841cc4bf14de4e7363c604310cbf1216d2634"
SPLASH_SHA256 = "19c9b1de9e9f5fb2add8c8600d0977322c34c94c218f81c632f088bc74db0a8a"

# User-supplied Camaro picture and its viewer; no packed original game.
SPLASH = base64.b85decode(
    b"000B?0000000004000000000300037005u>KmY&(003wB000B&00002PWb=;002&L000B*00001000030000200000000B>000B)"
    b"005u>000B>000B)00003000B>000B&003wBS&vBP|Nck%1dK0h02lx~EO-C}AQN%{POkqtN`Pko0Fo#`A}at8LGu^@AS(a_VE_P%"
    b"u&V$FW^5uW01!*_7yw}a1PCBZAQNG5u&V$JW>iJ%02nSS02Ckx<%mo22ml~VB3d9FX9gnJQ-EgrB5MEqBpqiIARQtdP3r&{A~qNR"
    b")3FEuQ-WsfQ-@~MEO-C}B1|9?POkqhPOklgOy7V1PIWAJ00bgTAQMim|1M15fB#sIa1>5;ashMzN`Pl5b^sO_(u1<R0095-Wd@SG"
    b"0095-)Pc0T0095-Wd@YI0095-Q-EgJNJ2CLAOcQx|62fT12)^XZQHhO+qTWywr$(CZQH1A&Wmk3Naz0matL$)F9K1?|NK)xG5{n<"
    b"6dKe5Qg<K#QOW=IBu{b=bO1hr)Kb(!G{RBI|M)Thcz+~FdH@<4XLM6VJO$iFHaB1ZQg>hgJOy+B;!ERFQO^JR76R5oJOG?Qyl((1"
    b"V*=$)x;y{~WFF^Ej0JQ6R0RvdJ_1BX&U^v?hDS4oFaVZ9WcXkv;7U;iNAWNKJ`-jNQbaxk2*&^qHizO0-$&j@NAYj~QO*D6Hil8j"
    b"|AbHP03=M`0RK*PZ~(jkWC{=+?Wl@?PzGS|1He;2z(wM%oB>XC=1!W%dH{R?au8wIR83$47~N6G|NKsMNaqFwdH{R?OZxuiFgyZ%"
    b"U<5Ec0)TP=F9A`=|NL?VVXDx40RcY%as^?aQb0cdas*+RRzO4g0sTSm00eXZHUM%1VTKeL5r7~7QOp1IL+=4Za1(NWVF3QJG%o-G"
    b")K^nNBuF4hZ~$@#ya8eg5FPDkia<~XZ~zbm&_FOS003$l;7w5mQwC%N8XbHG;!V*&&_FOS003+3U<$$jQUT&^oB`%Yusi?|Win?P"
    b"usi?}X9{u$VF3RUP(WY?asy!i{|IsbU<z^qVF3RA5-R`yR6vwK6v0u*|NLMA6u?o+|AcS=GCTl@Aiz<{|NKGk00b~E00J^R0RT7w"
    b"VF3OL(7;3Q2cR$)asXif{rpO=3It~cOz$9I3H(9t0Yq>BatFKtVhRu)?P!WXPzG=S5CzacFfafBY8v28Q3g{6WCR)=d<Wu9(Lm5Z"
    b"FfafBYwTbO!T?eM;%%G(=18zaWC|F-V7O233J6YhXZS_$287hWG8%9Iya8ki5FPEPihxiCVDJOLQ$WB);;ozk&{8%4LGK5kZ~$@#"
    b"ya8eg5FPDkia<~XZ~zbm&_FOS003$l;7w5mQwC%N8XbHG;!V*&&_FOS003+3U<$$jQUT&^oB`%YMehm_)W9+tZ~(jkWC{=+?Wl@?"
    b"PzGS|1He;2z(wM%oB_~MAWV?J;!9-&Q$rZo7}!zE|N3A6{|X>qHUQ{rQ$u6|b^vk!2f>s<KLS4kQON)5PS5}tDi9G800;*O1_}iW"
    b"1PlWW0uBKWNaz0iBs>5B0Rk@qQbKSWcmiR%G(3O-a2<F7VX%4td;oF-VF3MJF96~Q5IX?8LHhk}POty~ARpogWaLlp0PIZPKYvbj"
    b"00M+000Ek#PhA8Sbme9s0001_00003000000000000000000370000D0000Q000000000m000000000=0000000015000000001J"
    b"000000001Z00000000840000000088000000008C000000008G000000008O0000000022000040001n00008005u>0000000003"
    b"00000?0tQF6xF@=nVHSbMwZNmpa~K(8=!)>R5pf6A|bO8Dzv2ruk97<OBPYUi`T4#nm|HkLXd=tB)&WqG_dj7R(q?0^#v#|J0VC="
    b"F^SazR>*D=%ti^>%?sJx?980!oY|LbU<rEf{pa~SJ$%S!=jA)+{Lb(E-p^#Qi_6^r%0M|Ws|08k3=_w!Gwym@J~K@OfXZ0~h}GpJ"
    b"Ix0pTHKU_x<<zVV6nO5$f?;w4I#Z{fS-5h7@pf{kH3yiI(05X>05FJ-IMuWNQm)AxChP8c8_rR`FIfe^sd8X6FYp7@ti)QwI`9;@"
    b">usff)&}wobX}@(1Nr;utHH8G-vV8pdeu|Z)cfb;5O8hM)H8Q~1SKmlO{gscOFtLy{uuV${R!+q_gM3~!7S9Xb$7ijZAVzk(6I*)"
    b"o(6x;Tn+vWkJY#YJxNf1Zu^<A$}`nG{bn%nDRA4(AO#)U^0O@~Z+Y(!02;7T_dyvjul&L?5q}4|l^>(;s~<gve*XKzM`n??Q@<?("
    b"g5|wKn^x}q>w=YU&e}k98E+^0S80uA^wj<6_qNdQN7N_ZPJFydI~9Fb9-g{^_$&VWS=B0Ya0bAmR)A@Z`gF@Ie9y6|Aa9t^+_UKG"
    b"{OKkuFy8SL_*u#-&A(P!eCTZJ)VuI~7{dydILf5Ee)HH9>wfdty2lEixaIN39$veA?Rv0k?Q-kt$5s?Y4m?sg^7}pidaJR>`uOsq"
    b")wdh3xYhWZCze08{ISQEKm7Qkw_G>s+RH)5xOBzxC!Q!=XDqZn`h>A)#o9;F$IM69t}R?^G~GPLrH?&f{mnXK@ncUsQdo>GLmWk+"
    b"|FhBmU!(s|3jq8J;-kgra~kG0^f?`U0`&O<bg>3~-U@(#KX1dlgFfe?4+4E=g+6n^WsMX_^;4q*)Fd;wN>i_5VxBUL{yH3Le$@Vo"
    b"T03g^dlhOQpw@+&gjyMDS*Qh2D?sfBs6CF_YSijbJB(U3YS*LoYt(*-nhCWVQOiN?_o&@~+GNxgqNYU+|9&rOBx)Me^r*$7rj8)g"
    b"@b3g_;r_;<2L6{D^}mcqf`7LEFPiRubT{$8j0Yb1Uml+2e;M!E{Y(9y(eH|;xyo_pcYlf|O2`t_|D00eqQA@+Vqa8$4XGW~?yda}"
    b"c$YWh)j2J>_B)LC@|Jh?=Q6*K`l7#F@)~2`l+t}wJoCc;#)3&xz7vlS-;sRa#;fCL_5Te`ka9lONdLR*Ob>|Bg!#_nirGZOeZrMX"
    b">HBL<b8!BhCSCM;Cx!37D1&WX=#v&Mqg9eRuRWt#{_2Y%+&w3zlMWa)B%Zj`;E<hDLwFz>&p5%vSutfFJrqZPn`!VK9>tC7x%HHf"
    b"ra(rxPYCMaQO^@Xk}GP?O`3#ifbfjyo@3xnb^VuxPcEo(g4~SA3?LdFy=;Dha~!50VGznWsDOvbiBC#^kS4(f4>}BC@bqRDDl~+R"
    b"k`AiP50#zM;YbU!wy+>PF%7{J#Pe+AqK|?f>ZAG4v7QLRMq?D-C)GieDaXTjmBACvmq+l%t3L<S(_H9SMda+Oc~N-Zh6L1<fEdDC"
    b"tR9zcAoC+V_(c71<Fjk?ZLkI(TkaE7u1$!SzK&WOXHtT{JalKMe?*gykwA_``ve-904N9(HeeDc<9R%BugmCnFZ9H>yEzpY4*6T6"
    b"`uBW@yO(u^gf_89J??E<8@Z+_-JyOCqSKARLq1c58^Yk>9mykb(yih7_<fjBgD1Ssha(qlPYm9O#b&549t+_PovjhL5j>wY#3!1c"
    b"hw$`l2ycYSLI|%l1&}jB$Bq(iduT=hGlCb`6kdB_el`X#^BBgBuoMxR@|}QuEOhW`b0CD*Qp=Cv4Qw%wmIuUZp#kZr2u&s?hVTTC"
    b"bzkUUoF)+Z%^r={5f(P&>ad0j@$N$Oc=Z;^qum<17=Ro6E_An2gqDH4svvl{I)dg#EFWg$y<v?WqM5KSgr^jLzBNeub|YBfanD1C"
    b"C@CHE4Ta``jbfLI6T)RmKXg{8aD~Y?o304WWi41FsfU4Yg$M=p=*6>9)1eScE*JKzAmn8<2g$|ZYaU8_&OH$12Jjz>-wTJbfVJkl"
    b"yi<i%^lCTpY&+y5H}r<^NL{3V9w_B@X_E@q1_!KU@f8>P&@Xb!d7y=mgJ+F|(SE+i4_#gee+%Y9*u}f?xB`c?m#fYcyW7Y6Qhq%l"
    b"vF(EW!b?bUJ!K74xI1gSc+!E6Z~jv9xAxu1eciiay-RtxSOKuKnW#|^p1-9ezWg#{DdX(v`7141|45lE1?rk;8}#pW@<eab#S2hb"
    b"<<rb6-5yZ<r>u3b{o<;>!UmtWoPdFvygg++RMwyJ%-eApUZNF<8PC2tHE|lO@V@nVjgXdolAqL>RNW49TZTo83m)At0G4OLhM~G1"
    b"=v)E0$`+QJauV|J!~oxr>DznRbgXGT%?Iwzp#p)gT$9e+vu7f`O(6mUUsrwAxkpKSPVf43ThaSHMM(ZB-hw`t%vBv}D|>dm+wZPX"
    b"H~|irM&m77^8m3kzQQ*Z6mRXdn*wKt@>5FkyxEnq@2fq^1otg#Qpa;(u?r>!&bloPXIKtoHJ9jr(=yNDIxJ=RJ(t;*M_xYpPSfB)"
    b"&(Zt=Mf=1b9L?SYU?ik(>fq1^D`dj)x#{$!!>96E6au=kn|74zb3p>ra6D5UVmcKe8y>rCeh;5M^;$1r`krS*CB1agX$ZFIHA%2J"
    b"6H4~N-M>2K9X?fh_!#X_kh}`Cf)bFs5-=A}ZRPuIwFGUdX}#Q*tLsYUB-kg^KxM|7Km8r8UnJIhdgnpq$eIrf?7)sj#JPQTiBMeG"
    b"XAlqR@bVDnW%nat%^a@0+?2MhDgE<$v=Vf$LxuVF^d%1V>2y@!LBuYNNB(^aEv*?sH%gqJ7-;jJZGv(IX5{wr)BBsy=W%TeJggyx"
    b"OqB=^o}OWciY9{yJSag}eB_DEv|M^*2(203N5D4kDJ1YJuo&zsKRt}sXK(f8W*=MUD(CS^n1=8U!_x@QY$keKkXP<n(f=IdXi)Ht"
    b"d?zvFlH0scR`r9k)Zc{{P{-oS#laMK`Ut{%L(o8pxlrn|qY;S&9C9NeQMmhWbYS=tTCWQ1AujU6Z4%Inyo$$l^+AOjSaCVtuDa9Z"
    b"syH+$pytAQZ@r})h=jYVFuMY-*`1jD<;%zC7|RGYo{$S~Z`%*_R#lpmW-A^xr^^a1$4hfff{SRd39K+3s;P4o|K&RSaX@rtH{JT7"
    b"zfzi1*z7XRNdX;nV#Pq6EA2$DzM*zGtZOOrZWziCrnJUi?h~*V+8lQ-&}~7MohE<y^uBk2{bN7`c<-&tWobhSBfEz(vMicskdA7z"
    b"xAo$<oKXNb^4|A`?iN7(6)r}ab5f&4jpQNcW>-tHAli^c=gMx(NF1me0!)wVw(HTUYBMpg%az)WJOXvRWv;;?^tn`bxko(Zt5c;L"
    b"!_Lyh(k8)~Zve!_p?z6T!!^$nto-ud<{}!20wJ&3Acd(#mY)0DAhLvhYQ5YKo$~Ujk_SUf$+)vW+~j1;favMkSN6VpO&nn5l)ueY"
    b"tzLw8yMzUtidnkzl;_0dPKQP1=j?Nzh91l8ayJP0BC7L1L)rE3ZhnMhdtF&rB25Iuz+tz9ETkm$;u81T>&aLiI9ux8^C`p;Q2_Fl"
    b")5|L=T9A<y;QKT*Ts&bZE4dZZd62Li&Bx!o&qv6`EAJ)utG51S&AuYLC44ZyuBBZN3<$3?TLcLMOOwB3PrBBYs6!zJcDP3j=8~>q"
    b"jCW;ICZBpY>=xt~-`8}g8WEF{PFq3tr?aS?^jCFF_;dmw6gL+@3q=yu`Pkna8*hH;DLY<4xQ|R>!RaIT7fL$yF7N%(vK5nPx%@O<"
    b"u-njl6dw3AY*dq_J9?A-vHUi+J|_?39YrVe?aozp74MsA#k_lIZet3q01hwwW-~D)KZfnrvq3zm{H2(9wgAKe=#mlRDQ&OY@$;#`"
    b"C1lR$EYeP(&#f6oW`XiGh=XmX-e2{@ZRwaYB){^o*B8^*UX%DNvN_xF$^5gOGgLgnmGPmi{;pdzw=$pVvbXTO(g5Q6Qcu0r`KcjY"
    b"y=^0ZTWq}Dx1SndVLK-w*3AF5v@eL)GxVDa_e`yx)X(l;ed_SRi_3SQHB*@TTK!<HYR{7!*t4<mCYGH?<a2Rph-;ZOPzm9=%DjPD"
    b"o)sSU!1&{(hnt&C2#?R&zV4#)h<e)wwmCMQncJh9o6U$#@{7WFZlwMt-sSSJ2OVzS0k?bx;(L&<<(VzogY&^2DUOME8{N!9yMxDE"
    b"#>}wy2Is>K*ZbXpD#l-Pz>n~}x;p^T<@LdR2Q^%9ys)QuIA%a%Tnon^L3jv<;dgb}PhdO<=gBQjit$s2{qA`ed+4Kx2E~5(`yXpq"
    b"6_1xMCC9|uL%1_--7mDfgoHy)>Eb^I@!Fi3hxRqnjE_2ecB0qqNfr?e+|d1J3y~beE4V8*Ucw{LhD>6`jqH5}wlswL7r4mthf`q("
    b"g_+a)WIpPj`%4G>!&;!?fl^q`4#y7e@jZ%{b39=(1IF%f1?h)PV0c7^$HuW<80Zwa=Mmm;i~J`GbCV%RzpLP-*QW9Ct)aupEDNIF"
    b"{UJP?68K8_^8hcr<QP`AdkC%{;RXD%ld72;?4JU!(!Z?R;QEV0*$Oa$Z7}t8kYBb#*yh;Z3Bg?Zuu?G*V9VE0#Ptb;&7lhORSt!Z"
    b"jW;XBZ-=~Z<E9i~hCBADczLPF8ke`PfyQKH)^0NZWG{g<ul-VeC8HYPBrUhWn0Ul1;Qn3B0g0~?fthb9R`C{Mn@8GSqnIah?tm-R"
    b"i0~4TUFDZ1(s*G4lH`>To_HDHFOWF)!E*!c-Gq^E_NsV4dj&6<OLmVikt;kRdVVPPfo$f;>E}+w?ePSIyU@qQ#v{#EI>6fD*=b-V"
    b"-xkCp6TE|I$nj_Zn)!jY6}F%IHGudLlBMo}1MO=6E}c7mmHB9&Dg@ps^fwRQ4i@uuUX}muU|`9V7W?UsfF?5_O*=f`%Myqm4Zv+Y"
    b"^auT1uS2;C9{B)zZeb@Jyjfh#p9%8I1XkHw1zod6L6cQ1Wp)P8Ac;cP{NoGYKu{<{?rL~MCxng2)01Xd#B%RI2+!-OL{=G6uv|cz"
    b"i_Jrz+v9+nco_I?5Rbpw`lx;#nXd>>;Vg^G-F+cEC?c8AIsqilc1v>s--qyMsB95HVsKC$uq+0i8bYujy1NfL6waK7jAxa82+t#O"
    b"Zgc}{L+&~tu-Sn4rCE5$px#3sgGxjmERNvOCv|}POD$NAmV?3pr0Cj%cntI!dAB?b%(K~*i78nN0f=Xz+<aY~5HwkkF&@U#E*>2q"
    b"Mm7jx!{f!Vs!0F5Xj#J~z`g{PiD{4PR6N*Bh3!$tNdKZDovQDJ%n8Dw;+doHTnXs@IwW$Sl)RlX1o5^TL$PrZMvZqw4O5{&7jh1G"
    b"3E^?j!-eqrC!%THqT<c%#n)oIw?X41@d~_cBfJ8`K|RDAcA$&G^Pu@eY?3?|D#b3H7{qHNMWZEz7oi{dR3tY3812LHDP<n|(SQ^e"
    b"=N`cuhw$2gF&WC<c3r~MAf9kWj0CA7^c#xkBE~{%bpLoWbrL#VX*Wm4OCmf9GaxW>$n8A}NF#~xcpHv~ZYGg<85u7L1|tMa*dr#u"
    b"a|IkSq3pCe9}zq!Md0|xbRG_=1{VPmATMGTXmRU}WYq}$^4EoZID@Lmy=q*lErB=Z@%EAa5$$MkS=RCPHmHb{FTPq0yGS(l9e0rQ"
    b"2;Sm5!Xj&8X*e#^3#C*zvOX}L&V%rFtmBaRr3jR?AO+Fyb0{EG$zYAbqX^Z))JIJ(_Rpkw5G>$eP#%yBY}YO25Cdyjuf4_DKuB^m"
    b"!V5?QD{*2f#*@PRi<84vHT6{(PcHQpL9mE}L3xGx_X3!S0J=2jhuq02F1?P0`xN9<bIsm2DMY`)aQ|{{35Wh@Ou1m_(A(-lcsy(h"
    b"%a^K@)MN<zb>UcKpPqvULxa)xqxI_v*)IeK!+2FufjqGZE~Gg~hvg}gn}!7AU*d7R6RmEzVSFQ$L-D~$7_Y$<vahn<4u{5fM+M$0"
    b"YoM9t6fLjfaSEelke$0fo(`R-PaMW^UNuUVF$Ah$l{<vDpeKy?U??c4UeCd$G$-e(_WNXBPNjDDL3oU!VQ>&a`;qXYovtB7Ke{G}"
    b"N9lKjy{>{t?|7&$hE|&M%~kQnL0>BMcP9^r&5d#}$|x?+4O6F~Wr(Def)E}#X<dl_bi5j%!;@l{#zSagc#jtb?JG~|xJC=oW~oSU"
    b"dIN6QB3iNv1HrLWU_6+{g~r>kF0|eZO;K^=Y{_S0xP~Sew6D55nPas`B5T$KgMv-Y9hPuhk{}TMhI7Jroy8%%q^Rle6v_Ttnr~=<"
    b"LH=tvMxR`bcuz0|qr{EAoJiQ2;Srvv1p0zFRCv5e_7Oa%OYT6d)XA#jy^fo<jXt&v0aUED1w-&s*0#`8OS$|2pxgUksDJceSX@Q*"
    b"ub~PaMe;?<!e)$@tL19Mlmvw13-wAGe<aQy{4EO(kaT+!4Euv`goJZ*)bg!7jEogfp1=p`mxZ7V+BCE*7Ka&7Q?3b-x)eE&RSk{^"
    b"UTFF1$3?|`wH!16V_8bjf26u~P%*^Cqt46;Q*HXARUy(mjPSHGSQyG95urqYhC85g9vpC^B?%S8m09zGjw{tY4=R>%NUE2u42R(>"
    b"E~w&2hGHAsL2A)sPK5A6(?MF?vIk_I?ILn5#wk$R0?a1lAmOLct(i~~C^Oh&sw8ap`!u?8k*F8{!#q*^LpQM#nW&nyaKb8*UXNn}"
    b"15Q>QAS}s%el5r&nu6{(E#~9dn<fA@*^DDDCR(K1O-OU=U4Wif21rd7ygc$e1uZv>=R|VVli^3w$Bgtkf~f|y;DE!X_;O^w92T{B"
    b"K(t8hHPFbERgf1@W+nk52vQsOjOcPA5pkBtU?odH>%$*yQvC!pX&S4L+`z#O19%8&&_hBB&NC7sb@FireM&%IkO9DoPL=)c8nF(D"
    b"A0sRQaf6^IB<o!}<AVZm5E~%ZBTd(fbCh($$-TjVut;~`kbpjYK%ax;=L$C*Ms!O9L|9l+bEZY{i_M3X-WDDn12?V*aZA*Bo`|SH"
    b"%*QGXR>BrCk+-!3pzwHJ10bmu*kM!)(jxY_p=!i5r|h|iT^1tt+b@t-KtG5RB48Odc1Ggq+k!)jZ`_J*VDSJ(;ej1t-Qe#=jElH@"
    b"$z<HE8)`t({SYFXC830Z=fepp2^<ThN;ajUspnNjeLULpEr8Ji1|7L`g&HiL4kl1gLRMlj4y+RX&@uxWb|kH-+o-b3ozc;-2czKF"
    b"0pyXI-B2b0s0ArC4tb%fx}ZNk{6Nk4AfDfe_;AB&2@_m9Iutw77!h@Ud=2bVYduo!Eqypm?0}v`eORJ_B|*GF^Cmzo1BNRK1VSql"
    b"IR?JeDjbJzVngYIxF6X%@aGICAmf5+1Fah~(w#mYlDJcz(Opy5?*z2Ek1)u@33yC>Sm=DgL#HWd64M_eM+{J9bO|W?F?6AS+X$h?"
    b"4ZACnURJYWH(gn0H;xhbc2k4W?nzmTM@b-^gx1;{l<<fEbXZ;MkMn8dI3w*bu+H@Yz_wK)o-&+uy0VHvh%T}~%t`$M83dz75WhWW"
    b"wCjKwOA+)?(?~A#3cO>&2wq7^FzN`5DOWEXM0gYVtK(^$YK6l{E?2`Ls^8cSJuGJ5;iYEEM+jO1I*Bf|o9I!ABP?<LDvuq}!5=eH"
    b"B%cZ4@Uf9ZU`NPT!IncA%c)jM*R}8lOPF^e`Aj4u#1RFvH*7M}-AvHvRjdP7DJwyQU~rU}ac9kVFN-XUfYgordSq)jq^w#T*k&9K"
    b"T%`iU7a_66r~%YcYc7d}27B>rew8OQ6GzfPG+vP0S1HR<B3E>$0CRZJLuupo7Ae9V;l;&Ojo4(yYtRp#$6Pk@^<2xyqrxr*?;61~"
    b"Ukk4v7o?2H?An$qm?K^e>R{Y#i(}(?N0RkcEtnL6Yc@nBj-8=068SJ}E<W%Ilw7jI6T9Rmf+q*cfM!(~uCzBAuQg~~P<|*Y-gg7g"
    b"?;2>iJd%?%8n2~K*$;@Yjj60Crz3b0KR7iwy@POPCT#BI19oNH@HP6^33q__u(=YL7KL{fdeVguUPi`|lU=-*Ys(76F68xw00#_k"
    b"8_>=UK@4U0MDQHzZAy@z3txlAH1ENKfgbleurxNqctg|Ze~5QRbPiN@4I#XMYMr*dTLYH{+2!5CVzVpr06g29=;p7&FF_U!cyyd6"
    b"id}YpfbfDImb}g_eWOYwK4@<O`YbfVtKcaI=i{5+J$rgC1UIqXPu2Bz>Frd6m$MSv*rlI(VKA8>A99%x6&k$*2b!ScY|QGq;e#7@"
    b"!A2NRPH}<3{I7aH&Bt!WrTR3Q@g5#PUX~=g?QX1Y$@IV>SLPyY?hhP5qdIv7o&h}-eme9dFS1V;Wo$3CX1=Qw?ex5u>aVlhMl-t{"
    b"^2z3#{^}^?+~2CnaW9mb)BtOf3;DKJ#1hps6nyKn%nNMNnoEZR68Elh>Ga8LMYgZLiDuePzkIPZ7xwP6!y&8(@|(SNP4{d%o=zO;"
    b";^Dz%SK#5oe)*Z+VnmZIhU{&{XLA`i4Uw!Jv7$mVvgflFj%^a>+V~y;yX_7b=+fc(5N;UZU8!m?p0e-3PZ7&}@~vaN`_TN}#<!7C"
    b"-r-*Lk6xO&Q0mP?^n1JJY;h+ZW!gO3z(=^4<qQ5mi(<L`3OrmquN2+)EW&dR9w*$={6k)$6n#1MAG^;YyfW`kkX|{tvx{GjC2DS<"
    b"&h=3{)@?{`^>%Ey0uQG_{TGLxL=y@E?+;cE<d$ylM0lQJ!I?`lFSl(N52cdFyNcN5xPRFSw6(Y6iXhg-2c#?UX5#s{c(2^<JX#6g"
    b"mkS5DKuK99>XN*NKSDFZr~Y~l`m7lj_kBgAV%gX>z#cF1@%{Pkm8E_;W<mw{+p3>*&XAjWa`egVxliRt2+tX)UXevJJ3z@fWbb8p"
    b"1CA9qOz7ph_(p+)rS!8a1KvPvJVp7%o4v@iKlJy5Ul_SP|F(XbpugQ)^y@F0m<x(HUo<Dr|7)AP3c<~2CN=6d43U*rIffRfcvl!k"
    b"Lq+}`H}*7!<_my(^HeGFi$HPbuTOcI3s1F5)e{ZeaNGJugIXKMKnj-=vKx^eVO6{<>^A?!t|#3)K)HMCLC+5E!hI6;J8*mPr_)Sc"
    b"rn=QwCX!jXt9Ypp8RtbfEQ%e36dziWSwRQ=ij*yU>vyvI3@ESiUNpbKUAVuOYDMPp9$xXH`S?p2Hhb4xlJg$|M7sf4j*0DPnfiuc"
    b"pAY&k3wH*al(7BD*#@Azl)b$U<XT-0su^ek+nUgP2*<2BT1v=0_Twkq<pRNCP7#sglj!%_{KG1qa79L5u@}7cFKj~}e`*ionZIXf"
    b"fD*wL1&JHP&!;<c5Swtyx#B$tPu1>D1n?T%1zqj%D)YPVzPIZ08isREJryU-uj?A1JU}y4B%Pvb)?7NCBNzy7cMHM;Av|PiQOX0b"
    b"sS<i(^WV0vCjm%5BgUW2kaCN%PmV))?c2!PX(l!AQGiUi+?59vu{>1zWi}hj=;k8mu7YB0d4Ko=8Cg=pZC~zOA#oQ9F5ZZq+w#^L"
    b"Bwt|jp9F-*6~1r7c&$7#K=K6RopyUC%zB+a8WT?fO>2>>6llyG=#+9-9X?r#@Y;n{czwV*8brX{pE#8E@{vG2VduOs(+*>orTg|3"
    b"yoE$w&5>_c)JXGty7pnbp?8N-|DNIgbP~CIxqofrE6N36Mo%5^nTb@1J0~Aqe>J?K`*0x8R`xAr_j4zE-z`FT!<oJ=nyIu`oJIZ0"
    b"-SsJS;VKkj1wbaEsZ?UWl>5I_Qeqa-!=i&NmF^d5SxMl0Tr=bsAUrQGBYEnDj&0=z!0l>=jR<c7j<Og9qOyXMVF~nAkFpL%@D8*<"
    b"dndw6<$YY6yBzTgfcIa*c=mJENU`NU*bCdsgX=((?kt7aaJYngy_owM2B5tSau@7K(DBaPFkXw?Q^lN99D)LfT(trzT(7EeE4*5h"
    b"I(mAE@aVnvg0{zd<g|B)cG!{YQ08MiuYJ8lGk->E9OJpYg%LbclH*JOS(Htesb8u(f@iaxJ{d^e%OeiWm7!n7JLpI2ZI5(7#cLUI"
    b"MDRc{bYMIOtR0=09vQFOG56TyDH2};0ms{iF<u}rZXL}yWVj9CareT!#t<F>m~Pd2vcbz#Tljh2bI|JzR2OK<IXH*=$^ljS^}3Ng"
    b"<Z!q#zi`DobcgUJ@4?oH7j7@OEIvf-jo52$zHiz9yd?3G73to#c!YNeLe#%=Zg{9%Em_`I6&`P)qAuf2oHDvnj|xkNAr4teu7K>i"
    b"5Bf|K&J95<4~FatS|5L&=Q~uc0rM3H;%5~vf!?DQA9M782OoH3LPV^bHH7EG4&B~PWgrRmg9);tj(2DuM0jp4a0m?x;T4DQEP6C+"
    b"Fd#8JRPlZ~HOwvt&V}a3D?e3q!_b3XHzhR!qBx-91)7o9#~gtdFkX(=ewJ48D3By_!5AvU5eyK2B8<n$A%b|7d`KgkAh1Z$#1ZgZ"
    b"a6T@=ja~*iypn?HCp*;nAny7~4Oa*7u`lrbiIKAQdAq{=BHdt}X)UO^coE@IP<~s*b9DK=j0_zw<MG0t(EOSwsdx%y4@I97JHpek"
    b"U_+RGUbaVY@bjRj92xBAl-t$uqMPom;R3^(R6Lny)G9Zg9SFvXcqpmXeI&dF5;uqWWuU+(IN*cuM2?xf9u5tY>#$SOrqDHf(auWD"
    b"&xi=c<!YSU<_)O9DK6x$>LQCI>D!3^cG|=KSn<Q|LrZ}P4nq}BUM0~9Iqm?Vm<i51*FK=)={E-bUjgUBM{kmf@SoS_@G!|X7i`TE"
    b"fXVAq$VY(2+gq&A3A`(Cx3U;;7vOHF%F{g(|1lCSz7$?kH)o9>Det6rgyo;xElsnvxS$U`VZ8FGa$Thepyz^AmB4e*qjYQMW2aZ8"
    b"pGPes54e2Lr)~z(FN~qz_SoH>RRdo^&%^3BcwH@V3>R=TCGgO8SkV#l9KFzs@o2Bj?m%vbz7H2T;QlSXa`TP*6F+RH<&99n4}<mq"
    b"V)-=aRoqPph;`qQ0XTpbO=o#9fi+Ozr~}PR$TZN7sPxFD8mK7i&sV@=c*KN^C1_I~5CsZJ^!eUD=0Ny%696B0Ir{>PHyh&Ot_r}`"
    b"cyubanFBG#E5l1)=gD3*;7uUDyI+;&Q1bo}_3wS`U%Ks%##}T&?p+5Q<_Qf;bq2$#q;#b`#mmuYDn*1|D1ckgw|gNj%7%)Hhx56d"
    b"?1l|^Z*guglCLJvn*^W(DLpac5lVaYJhXz3))To3v>#R@HnLQF3#X>8A+I=)KF61;$v;s?w1&MuXH2|d=XUl0^!6W9RT)(C?a-Hu"
    b"=fi<_5ZHSmf$`MPtkWFjy;x%6^>vesm;drx4Ny}+=MLj8dg$${+YaA`{QHVV!DYgjo?k{><d_9<2v2sN0LgCnWp^zV3<$NU0bN=j"
    b"&RDwNITDBP=$=yVKG+ZmIXPo)`9deCtpH7`tG62Dgz`U_Op6l2H#!D<6vAUv@*Rl8S7OHx0#K<mn-(AxBuZw4a+L5e6uE@la5fV9"
    b"aGek9z@ee$3qRi3T#S33XTD0jiPD&+;s*-Ev~aLZMlys6g~Mz%hf~E<ALc%-@TGOV)*A6@cuJ~SXF?{TJH-O*k&Nbz2#@z3gzH<N"
    b"3yL+0K(c&vgdScc{^#YTGBYq@n~A!<-KM6fpt~4OP#A6_GLzJ>yuhRW!9d#(B7iq=t`}KyP&8j99@dW(E{X9h`qL`O{odCdP$w~*"
    b"9nmWb!p_$yUNM7`QQf<WIgad?b{Ej-Cd;tciGvefsMz8Cc8QRfT$~H-#S%UR^^X_`Ks5>M_M*j9F2#j+2<^QbuLUzZ5&|BAX~GHI"
    b"jb1w(q%fWgeJTT`<Dvm?CydHKOGHRmB^fWnYqSYKsNl{)Ny~(52zYVPd+Pjp(GQoe5Bh|0?oq?_O!JM3(~a<-mTRSenMbZTSV2a@"
    b"-wv;y$DPH~)8|DxoOO(J4&%)Z;gQ0q7=FN)3dM0I96gi)DTaB1uu1wzUpku*cQBVtM@?-14SGtTkfPJz%QsCEkSMSt16iSX=|>T2"
    b"HPygoz>UTe_$%;;d3d}|F9fEkU?LJ|<4eI5M6ou`u5i3>d6R_8N%%HcwI>1S%CC(#AM;;B69mq5P|ayTBCt?Ezp_+%vc<>u-E8Ad"
    b"x=MW8iTw(<4NQ_p!6}*;c(^##`&!Tx79d-bD;g4rE+-}6X>a&u8>K+WgBZ~tI0J~lXgr#`5|2YS4lm*qY&Q@J%T~QNCxIC7umWIQ"
    b"P*aG5pM6j?GJa&TENB{ymlVUFHX}TR<`v3}oMb71t?JS0L8AwkVzo#bEe`cL(aa*NsvYEymIfX=8jr9<3a|##cqo`n#swZdS9$(f"
    b"99}6wowZ526F3qoVr$9^JB<0Gr^CZU`{(3H;k+jYZ>$0-!SL}-;c_q57q!2bh9^Lpj}>u}Ev$0$qXhyr5;p06(gBTF6L8KF1Bja)"
    b">3}i6oK>ZlQrUuLEY(Vn+UQ#Vqc(q#Bm1VEi_~0vP!SU&tH2{tBawaON?pOi*xQLeo200=ohk_$CWQmgM}U|fHJfIDn23NPuZ}sW"
    b"qRm$%-&Fg`cE*a6YlNDVoy0_?!y-G~UY8>2$w+f3AQm36o7-VRqX`uXMlP_1>lComq<p$7@Ss#5vwreyNU>n3%#o0QIUf1;VV=tH"
    b"3s>U#(qrQ7=NomwYBA+T6V7Cd{2`)KWd<$pAynmyAC`DIUPo;GVS)j}7~7mp>O`El@+APwvDi0s)F|I+?>GUSX$ve2GW+_WL^b$t"
    b"IuZN2qaf$%Te`#SFR67Y6o4tgS)z3MX|=H*D+0n4qii+>=Re2VsUBZ1UY$lU8(kUw?WW5rSAE9VWFmn!RyUkj3Peuq#n!FiyKYsF"
    b"#xsy$$)->aUae-)31i-CFpiB)YjnX)(;f<&-y*qV%x)1$*Xpds817ICF@UVfcgB3p0&$JE3s45PQ<Ve#M(jb|$v{Cf<_)>}vAb7C"
    b"2Q3OCh<nV8yJoH$^ZHwsj@`c;8XiM4Tg!qcx4wWmohci0yvM|``xl4AjS)x|&YiKVMfF#T$6Std$`u*2k(LK$QaGNZtd~M>enO&q"
    b"yk#uB<D<`x;(Bu7_=^e!oe7%TA5B$xun~$Ha?BC+=8UTL9<||&v}9KShhogWRDERrTqLG^Cdf)-zoAJpYSog<M;DY=mjwmsPLcIs"
    b"P27l<oO4VLqjk}BV$>)+qB_45dQt&LypVUqNej;GqZ<Wci8(qPe0f_aMz30G<0!n}-nB<6xgk6A!wK8|D+}jSp>O8mhu?^*QoDj*"
    b"?i_W3oIYw+W<9E8Edx_P;tk6%+nYF~;f)@33(3l>^l#;8VP_fT{GV%-@#-~!-RrP$zM~Kc1cQX@!oXcuq2jDj-}HA*9l;}ZzS|J!"
    b"(Sm8tyoQ(Y^b^P=H4x=$sP((OhilR(qoMLHqIVlB&R;V16pn{zkpI&29>Fibb8+Kk%P2Ne&ay-g|K3{mGee37kV`5xc)Awg&>X=%"
    b"jYDx0uLuNPxpe_oYe(a0ExCdf=nBLoZ&e7bcnbvd3)+IC;<X1F8s?H;MU#2yvv4+g5G#^#J2Xhq5~^Lq4qC2_7hY%1-BC0#A<NeU"
    b"bVVT5jH?~=fU-j;(d!xY;-uU$#a(oTT--%u`C5RUH-q1{nwNt3rPH9Y65J-~qjmd?u~aTuGID71G|?+hHv<g>=Id(BwSWMW3>!{N"
    b"Ry5HBjBQng$6FC~%&URjOGKi{N8Dg|UPeq}K?H0>hT4Q^BHuD5USgCcbrdKY^a5}pJW#1D1v)EoVH%ATtT117L0rx+QS#3qGteq#"
    b"kwrc-DQ*SU8k259{)`d8<3g;&PE3;}>aAE0_w9m>6noQLr}njsHQ1usIbALI<iC!_i~W|Y7{QacCOG^aO_RKn9G9~K8HMqn0>5d5"
    b";yupq%FogID7gm0z2g@R*!NbLZsEI-9k=B(8<Y&-aG&LB8Yj|X7!k7z;PBt((gB;naFZsh#sCNbhd)6&l(J$_{+gnu%nmOR8XD?!"
    b"fIhLGGXPS+(S#HWtK1mdv>Mw!-iU}*kw8Cg22-0(C_K)8HSo}@(X;Sv^Y_OaKLBAXVHJqp;cD^3{Ts3Qj*};wka<)EzIUTvxd7qw"
    b";Bn?Pv10L3!d$XY0H*0IR2sm73tPWGo_6+12$$Z9WXdNX<yX~t%MjlhP1r(Beg=Lld~dus<!x5kFC;@(rJ!4;c>|;ism7ZSo@ZMp"
    b">=3^<9?{Q1`J*p?b)cq-^|b!rNBFf?DcBo6DL25r`tON$-8dW$QJxiQ^K3uhyG8ArfV>NoDTo12k|gv$@crOY7f&pP$bB|cfFdvL"
    b"_DsL^MQuC?@NUrJA?pDx%`|>5y!fLmJVr?6iEn1c4`^QMuD|gV&{-ttz9qHlwM#C)@^9ale8~++Rq!UWk)Xj5zcAq?knWs__px&}"
    b"51?$n`JNN3N4_rfu*dZGI;s-Wh(}VAND2!9G_Ml%s*CyT`@u0j23N&Z2DVu=v!8!pJfNPT;8D6abrvA^xf?rcl&gk^W43W!p9xuj"
    b"^Ks&Ns@**IL=`Oh1|e`A9F0r#fu4iPSTmxYV}dpWQnY!>M_Z62dAf{kU~N#S!Amz7E>Pw>wS<8Mshm>d5UtZxqtTQYa(#`oN~$Yr"
    b"YRb30sJ@M7r#-lrhYDr{Xa%Pg1z=`!0jFWBxB{rdLgfmFX_UpTo&NBI>|j{;>`Q7kz%$c^euUy*o(#bV7$>L$ki)U73;`Uo#Kfb5"
    b"@isaz{MebLX}Ijm(dw?kzS|kr<uMclcZa}A5%1>~wFbItP6{yA<2`kv>X-!8h8FM9Re^#59tKJ;81I5!91GXB2x(<%DM2H8*sU|V"
    b"uy5m2BSqTPAg|~Eqf~1_G4`{Acph}WC)B?X9;NhlFKhFv`;35u!~m4vQ4?I!r(fO!IRzJ4{{XN`Wj9Gx=vgHb1V;LY@Mw?PKPw1s"
    b"g$7SbpEdezkmm;+%KSU>L-ojZ2xW(S<P+%O-OfBTFa_j*sjP90tS63dMECQm&P8}^5O2iJta*#bu0f=l>yYLLJ1!EcJ|!k|65>9m"
    b"K?96N%1NV>MHJC(vhEUNR-Q(TwhGP$58;48IbYy)7Qv<#r3<!0@T<8FAIkyi4*Wh3=bgyYWjjs!pIl=tn}7gwVema>0__AVkQeBA"
    b"-P-__$HheG>~qE+!)(k+`HK<RCN?N3*HGqE_zh!dQZD$=%4n34X~d{O=2xJjI)$o7EUY`!G)N+AXdz=A%PUlaN8!-CVo6u=`Xugf"
    b"jap~0{1tEc8Bl_*k5Bwqu}}|y%EANJQf*u~r{<j+r|@`<D10co?#qK!!{8-c{YPZ&ae{j+kKEdQ4ZI2b;ZWJNmw2%^g6GA_M%Qk}"
    b"7x-Fes1^tS(>*CkK$~Q^T7W9lZj8JYEb#1j#K~AQjReCt^M$>jdy=}6b|ZUH<EgwNaXGS}Yt1IzjW}hm?lzNOg9mN0AN7k@_eu6*"
    b"2PxC*w79`mpqsb0RZk=~dotE<-VBI2(WOn(N1$1891>PT8+kREib4J1l5;G!B(xym8Bl@u|F#sWG2oT!c01MjsPH?e88hDitO9^8"
    b"QEwso@D`qr3v8pZ2jLH15{>*6zoE3bxyx}PAUx1AZ9u_wu!ND7a4?$jFoBmx%r9z}a(l7lRw$R6ZE}R@=8II>pB0(nPEyh7%H94>"
    b"d2dh44E>Tx{Z{<WifH+Vgpm3s4J6jHXW(qhPBp!;CsbZ9jYOG`1KLL+YkFOm$y{!hn`-n<FwO%q!wL$^D<|a%iz{BaeTLnxq*u*="
    b";aq47#`8MDdxK3Ho~mip&3eR2vlp|Ep3_y%%N9UMkr2U~YC%7O;>uWTpNEhn!Gbq_$Tg94ZKU<4#@VYXPjcIwC7S%b+0P*da^vp="
    b"Al)M%UyVw`@~S*a0ZdIfj@(>Xt8OH5J4WG2DpQ^Wc2ReOYSS&+uS5E5sRh5rHY2vYnraYSn9C@f_;A6{pp{V02?o4@9<Xmf%VbW@"
    b"jNd6_1>-E_Wp;j4QR_6KBDoN6m!^W03vG5$e|~i_m<fELMHY=+mVDv^8dyoL4QS7gvc?mfQ3CdkB%R&ud3|^R#tVeH=EpxJPPXGu"
    b"Q4U{wA~ZY-X?)#Py!K6oTn_fPz_@V#RCypFMwBgz%H-n4f)G*l?0rxo(0X*ncq?lp@L6ty?Htz_Jzm&{@ZJQB%9Oqm9&gb`3%Y~t"
    b"(ju)cf9)LQdyF?~B2roh#0@s+EJ=0-?9ef?frQ6NoxCRK4L}*cN|kVEvm+U|xD%s=vqlpU4L55+sSS2}0PfKUUN^{x(<cKpBYjRS"
    b"EdzpJ&?DO;6;xD&_k@PmZFq0fbwwmFnvp2@Ml|3hJF<hfd(P`h{J+eZtLAGx|D~knefGyWhGj>`o0DhVt+-EWs>Km~rin`B^6(^s"
    b"=y%jv!vC5Z>0hV!b)`PboTJKzjpN~$R+rBQcV;!W9Q`y2{>U*ZQzM6^uPaktm9fRl+8Z|msbC@Rh}us`E5aQeq<ZD2)4X4gh$Lb`"
    b"VAtoa=<M>4nSd48sL6)P#*F$(#$G9ahYHNW$D9kk-;z;u;JOK_guVEL5>*^Z<UL#C;6|hsBamhqc4B#h9+KAUeA$K^$U|ubn<M>m"
    b"1m7vTShHH?#&3QO2eTS?K(H;VH@|EL!#KP+8R`t0ZqSMGR0A8o!@`}8$XOLn)-cY3$awLa9EYEL%`+jGLci|E->`Dv)`uQo`_C`v"
    b"xnU>}z<R}rbCe?B8_GrOm<9XSIj<5Fz%2>nqWo?Svu`ujZ<mlg;}dFdu?5CUqk@G;tJT7xv^{;FB0L<)#4<09P#j^Qo^hfx6#yIj"
    b"{e;_RRDH%pQqY%_nXG3M2P=XkWnX+NNIF%hWcOW&Q`3@>&0NuwBjHUr+fvt`e&)pN&IlfC=K3D=Dr$8jRBWZPQL8gALzLHAESbEV"
    b"G&;4H5(*ciMQu$1n%Ph{%UAhKYw?8$M=4+MeJ{8bXYj2NhN^SI<02qGQ`cGUz+saxk|i<#y)Zg>bc6fn<GLC@b1rg^;HC2)zV4%B"
    b"b-TD!I|rMjBrsqZWxjFf+38mV{w$VI)Coz7wQgO0`$r#jCr9x5l%xDNX&#WucyWT-w(<9vpM~dCu1=Pp)`Tn=G1^)S_7aUfb6zcX"
    b"qTSh7b72He$8WnIUERdv>Aq3%%oa3GQX`(n-UHMLDqec%?Jbw5e8$_q_|2cvJLO7bY1jjHH!u5?W$?GZsz}3oLQ7@G6n>dXoh(%*"
    b"PbsSqYOhGNMGqeSvbetC+wyUjA_;T!fB!xb%$%k=HCp@X$grr|xWB$yJ$5WY*<1LdKeU(psxK_>F&-#SXX=BF*tmxp;vO-t-e^t6"
    b"s)TtoZtTzy#lOS<;_zTrW*=U;UOQB)LJcJ=a+VSBz&R)<7u+mhnNF$<k<_0zwu!H6`9smKeEm6JjVk$=<D(K5tJ@2udGCHChO{=)"
    b"z{|_lY#!U<CAVHYm(`D!e7J%J>&;9*leGr$ZZDJ$o_l^qHGVS=RR>DajPH=Y9~-Z9vv;beuLVZ>7eJHn6DJLO)YPb?S%qBK`3fT;"
    b"?U4oIKrELbx_b#*;WCe}X2k5n_A}+=e7Q$4JHu3s8LK<hghDIOzW*AjTL$zxHV@aRW}gzqo91K(HaU?%@bGHcYRb|k5*HO(fVcM="
    b"5q*try|3eu<PkFsnFq?ePNkvUSOAqYjesQw2@*(OD#LTg+gms`9<@R_Z=Oy^2{D8>BjMn|5_3(n6ybUS?}sh5aTS#38uR<`Zdkuz"
    b"(THHgcy!&yq<KaL`kHq0cGIiKaKUoX%Lgl<$L`<5b$@(w!-A?v`Jcqw6~`9kUxy3~?1ze3Em2l+a?#{#9n;6g(=Di*JLnPTc7|U!"
    b"j{C<{N-ua`T!4uxSe^{OK)NTd)&Sr&#tW9qY297KO~h9MALbV&f&PNpdv=^d5kv0_$XNyZe`pAVU)4QUYnQl`eob}lCM76h6b|9V"
    b"cQ5$+v2kd8f{6*L<N(|i2))U9Y<?LSWM}yv5r7bH-^Pdfm&yj1{$B!RGQ2ptPDOLgAi2JO`2LB)EbJ)$#Jo6!mlD^XE=|3AWYMUp"
    b"SJ)?vzh<mWGw{JrHJfo|3II1f*`k_VO6on<2H$^@N;!UAl!p(RuX4AC{hik6ycXWjvyU`1)(3MNc*iZmdmusDnKhAw(yRFWw$5^3"
    b"o&YRVLK}F16t3C7r<U{_)97%p2U+~T)8qFs8fNfmPcqY?v<Tc*ZY(zw+HU+d2tv@%Gc?!2%YUzIbKFi^-3YIH2I~xj_rxm;Z`cdn"
    b"l#)NNLm*Pg60K!2(rEFOf4o-sH1G;9O(0%SC{G(6%j)BRlM`nY_vI(lbFfj!A9ypxEOaa@Xm@}~#KJpjuZ8z>`$OviN#WNo^BC|J"
    b"VS#L*;m%L?ksRXX9Y(Y6PQ3|Pf<s0SfAhdKYe4R^`_>54`=Hdr3Go<ExZx*&_4;bz0TxTrnL*zcO30I;KWe#V@SeBrE!u>vQN&|h"
    b"J+8<wXzmgi*zyza4*Uw1U+tRv!RF)mwfNo&4~XA#O}zPz!6Z^M6Kk{0T<=480ZcH(2mbssJ1#);un&N{km4v%jnEm^YyTmRKfrYF"
    b"t>#%;yb)vG5a2|#piD%|0XNJ+c*FKD)T<o0EYS-Co@?U0<!xUDgjsAZHmRjt5&u;V!?=?Pm2%F#5cZ3~keV8V;)5^lA6q^jc7ML="
    b"SVg_@&O_LM?8t7?=?DXJCgJ=KvYG<0vz`s=DSv1yc<cn+1S3e?Oc(%}MCO)(RlC6i@GhYiRyTMSbrT@>*ULRSvx@Doy%7eYUZx~E"
    b"%^HnB1pjgcQ5*7!4R-*7FyI~3q}lk#C&v{&4>B~xTh-TgNNjDVAI$yuadBtLgRj7b=(5-fF_@u7{&WSH(ODbfZ3ItQbOJI_k*?QF"
    b"ST&Uqz^;mIOD)LsM7PyXjME;XHoRJ~?Cwg~IKV4G(^Uxz7V8eD>hTj%e!mth)o6^(tfrj2FV}O|bkG2x+n6z*$FI)vlrVD+{3h;="
    b"We<vH$s!)PC6X6wPD`EXIba~B30lpB@t$g(A&5sDn)`;<$jA9;r0S<;PTnWy=s`SMTp*nQd03a7XKxi|zK}ZQC#|}m;cl3QUqNTd"
    b"OE6QUpXo>tp9C2@j%^G&{saLuf<fpZK%Affc`46qd=LC=Dj}p9L4`mIIM`7zM+CQ6Q!)gSn(bEHLJpJ{pfUY>$|eJ#z;(uSWbPUb"
    b"A*+>0WzM%8Ju*xF#8C6Xk-S@MWSQAAjqI`rI;)l<aCJ3%<F~7CS(9Z3^vbnXy%9O%NhY8(8>bCT%?L2xE_$>4h5p%1<xgX7oIs>b"
    b"-pqV{XtVS)z>vB3x3mqFBVn0n$s)A1YE>GI@VX0=e`zujp#Cq&Gq~fYsz-@X-=PT)E9M<i20XJrF8|P}){7WMrB@PM*~o-gsJqT+"
    b"43_<|PL6%%Z_53@_smMs-!B|B?mqLVeaT|H<=@sH688eG2oedwC^RfI074|pX<)s_g9vEQZtV1I7Po?_vkY7+HYV7BNIxTeD&OI$"
    b"FlfN$?E45EGM=%!kp?fA5XwnCos(suD}JZb0zq7&-RvxK0;8p(UkBLuvIP=tt=7G|sK4-Y?$vVapU~i@lNZixcUq5E5Pn=&5O3DK"
    b"g)4tpxtl0U_sp(ffuzgJkDosq5y(u}86W<kc$+1@WATrxj5(j}OMCLU#7T<=YFgPBbJYs7tk)eMK7Y#>o?~WBAQLSjA~B@~E8rrB"
    b"pD4@g%dfOqB#@t<mEr!Qnam53PsDu10Osb?u%R+>Ttb!_M+(*~KYG{urqzQ^p^hv(d3?p)+xg<T2v0W;_JDHAlZL2X1}u}YwlFh)"
    b"#|AZy;t8Y)l$pS+3jsvkR}OAY$jcC(QspH%W966Kv-_MRL-5UAMcHl0^z-4eQSbQ)l$2n_)zE0#D3H4uq~JTWg|*vO_C4ck^|g?L"
    b"Pk8~jvszOz@dvNIk{66b-PCdJ+j|h+b0d}a2+!CHTe<k*<nDscmZX!cGXa$U3RF4?L8r+-xBUapIG^Fk*S}8Z@C$Qwpg|BKrVc%j"
    b"vv|cjoBjd_7RqgIH9l?BJPqNi_Qw#O<F$ke61K9l%0Cn-7npdXhH0oVdB*jd<}mFVPD(Y$Q*%uOh`cz2E`p2ccPrinQzD^hA3<ic"
    b"2ms+NI?3<Pt@LnbxpcUE=?h(&TK53+4X5$g0!wmQyo*|-Spuoi<A{SfFJuIN>DA6#C2YP!7YXC}=w*71hUdpayPp&JSN!lReo`Pq"
    b"dche7n*5G#zDO$eZ{JWeRJg_RQzPzI)ZfTT+U9yczKQ(h&xPKg8@53|(Ns$=)vV_KQ!eln9)tJ$U>AHz`h}Dv3Lx3Xbsr(hnbss9"
    b">tXg1&#n8pd2xvWu|cS2M|ZN<O0<x_G}m%vUDoL{`ALt6v%nP72`9fvqCJHTkd_!Htdt0!DP>wHa#1;?l_vX=&&Qu4-ZQQJ(H4_Y"
    b"4F7>6jWW+2VB_;9*6B#%cON}_h}3<mqpF`Ipa|)1#=<q=xVIIGrlslCRCiWY2frECNL4<@)8x~%YN`JGO}9P%8TX$8(lkhgr3_@R"
    b">dn<oc~KCk)Pc;!1l(J(Ndp#``BsIJ#yh#qzSsL%K}q+R7gPfzKR)B%fCnY7zi^-?5Wi(Pc!Y7SV~04QyaO!OlmK!?4Y#{IaYsga"
    b"e5>Znal%N|I?V}Fw><=#m4JVba%A@<*CpFu75^n8sgLtb^Z_0yrSgnn#?#`P+<)JnI)J;2ImzuUzey<Vuuveo$ywsd5FRxekuKY!"
    b"A?h?H!V0Jo{-nYNTH13qdtUG7w=0bv#JGeHc+8Mcs4^Ojm-A7`RVKO_ClEPMPHd(<dNA|0KEBa6J+GJ~wM&;8e`(%IWZYujG||V2"
    b"<>)3SU!l+*uA!Xvm<WVn7t0U9PBl5fpG}djhm<_m$MkdcN`-97F${7QX+A(pcTC!*-#nED`Sod=zGmvvgl)7}fde=_rv{IZi|Z08"
    b"i4nP0z7~#Cs{D4}Y#$@NrcjE_&w5xV)WKqfmF!|%8_1QCcK#`M>xS8#+|lw1f3?vxF=a+KoTe1C!!IBO?QXbBZaJSM&u-!l!)lnM"
    b"%=S6tLVuy0<fDd>A?3C8!mV&NwD;M?s!f$&_ZgGw%YO)Gd+o<zqbyPnBu?>u&EG4x$lNjbf@1qdnJcsBUy)}Y<DN%&i<FoAjFKNH"
    b"^t~p1j<Dg7y#xLU-m5tL_LJ1h$X3~L++3dNZSmWW!T%$Vb8>^q+)jAE%yz>w@cv=G15T5f^N6tpSgGVeTA}gk@G--bLJu)M&ciuj"
    b"1!8<O@CNhe11{ko2oHbd^8)yT6BRTQl~RI^6KBvq&gq~e&RI+O*uA_HF?yrKpjl#k$v#42A%hkWUxnyWCD~!FdAJd3$Vn6h8T3%z"
    b"0h{ng6|{@6%8lrZ<`>O1Y=pHtGW%JP7kELTrMVK@Kf{;gBidLczX#1zy+TNghwb7(p+f;bTz@tXedRj&=cG!Hts7Djdj`Iu6nb)v"
    b"6753})K@@L)NfnNzrs6}3(D&<+fN5F13#7K`nhl3I>EKU$E1DzHaEAKhKLPsJG@cu8Y<|8A4)dw1H*jdu;Y{x@a<_o^uaguko}KJ"
    b"XF#w}{cIzDh<{U|;XZ#2>fZw2%}TP8?_^GJJ@QXv@1U)l`%fy%dX{W1Bjl<+hqLq@$#$y1r)2oqLFEO7>9YU9SLL(+RcZ8rM?N29"
    b"8~Ee=ol3q!4@1u?-_wDusN;p_nT8{qmF4o&gX}Y`aMVCN4UWp6Npt&bAMx)h$^R%gX(!Iw&MA#Y?#i@l2a_ecM|ow~tVb&@9b^bJ"
    b"u^1rzt^=CCfPa96ge3);ON+q2gB{poHUa|$(v9RMuwRds^Gzf+lFb&alLTLYR)g70A+y~~XpkJ<Y*=p88n3TUH|R{ra0AHbAw;vD"
    b"5H?NJ5R?uW%@sxsc?|q?)pHulrl~pt7)ksW?~In2n}J{vG=iSgR|2i!rv{L2`X0qV<`nSH_Rsdu_Rsd;Yn#FXgxI78t*K{LfN7y{"
    b"^$&1ZK(|<L9?9o4Onlx9#1uWa@-HuhLgV-_{yRL3n(#_)t*Mq~P6b-$NU3v2D1o&Q!Jh#W&DsR8)R*A9O3mkl=)^E#coNJOs7*k9"
    b"U&1(C;+f*q@IfDUCb~|e)1y<?8eQg9{z59-mx`S=0A}Fl%^bJiNAt=ukc7XPL{RUkZiKs+m8xY~0C0l<9_^INdH-v0Z!EYOFo4FA"
    b"UmL>9sW}9@@ZNBIGqULb1sfQ6O5I9JpTI>^OJPS9+`#+k*fHK2$FrXKOt4KS(q`cI_2lf%JZm`Q0039jfz_z{%lmRc;#_Q^&)9~u"
    b"GZv>uOP`rLvuaVypeOz1Aps<C0?^TF|Lm7OZ|&Su3vBpXi2z>U&m`3J72_>|c+zAT2Q9O!zO|m&=ZzVYogwCmCM_cxzzke8k#pqr"
    b"_75p&Agj>e^uIx~exSe1_E7+DJWddS2Kl~C&iR#%9;dC?6$@{bGj|m{&r6lC3diDdpQ6Q-R9YavLU?#rBO`dq8Y;Z_^}+Zr&upM("
    b"94pCv{Szm}CdS0GI?Jr>&cgR9_x}!xAdWe|NCZOi^I%DRu-3mu*ncbHWQ>OyWItFW_H0O^JXFCizld23$GRPgv~Jz~M}9ls2{hvy"
    b"e(?5hz3>L0nT5{1h`iwP#dEmE*?8|}IeMO5TCi98*Zvj!K;pQyG5OCzdMN#m#Waw!0!`v|FKiip+DYvN*W-xkI=oAJ=A5TCFF}1H"
    b"A94ci=95zkb5^-Xi#2g(V$2CH^*C2amBgRK)YSr@s1!5&0I++7Imm`sg1D~1F;jEj-xDY^xC!qR+1iuTQc`mFKiCcL8e-y2FB_Na"
    b"mTF$uVV||o2dMNNqO`7-c@JQlWYrD;99zF#!Vl^Z{iYY;P`u~=bUeO3^AqRx2^lxU>fRjVmdcl;8n*6*nIgiQC-0>^XayUzh<*&h"
    b"W3<C%O|Bgr8m|@g$CohU{O{LOUwY2(Cf3Emn>cOTvzvUo>rziI{1DOa_N;C6bJYYT&V5@{ePP>7Ul}zpXb+}q34a3j?Y5E?4NhgZ"
    b"p(ECKC#GvA#7l?XVSP8n=`dbbVk>BCyhwEb9gczQHkRbx+=R?}Fe4S?)wB!>C5i3ll{8b#D0!_BFcqE@f&<gBv@>N1v<KYM*h_Z;"
    b"634Z7znE3L)%zI-z#=4X$DgOyr0dsR*XfbcDr4fAj3n#)u>o*_dh=(1ymdu2VYSl#b%(iIAn!rvw}Z(AFH)c1f>tJuv554R++P$k"
    b"YwESR{+RMA*FwyYQb5@%X#B7hfT;pgxwx|9hyPhHERc8LN_A3aDy$-BA$~!MfqJcD3e_rjs-a+}PsF0%O(K{`Z$^TYG7+svhpg6Q"
    b"BIWUGa)l)5)Exdws`hsE@1#>At^@_!tZF^tc$yG}*wv?J0JRiNrNM+Iu)%1?%k;$w0;pFbnf1;%0R9-C2SBwED-`0lKvNH_K%*Pu"
    b"FTRh|qZ;r#d5FAGXQyS26m^IGfShHloyL^SGrBAb-%n=6PP|wEC;ZdM_<yTWlSZ+UF?s@t>0#&0V*ajphQ!F8Hmr3GqZI#4A{4rP"
    b"xa7Oy<%`BpC$zW^8bkR=*8$ZK>MmUuyBhn-Hk-@~;ZeB0%CIzgDSZ^)ard*K@7h26jE)e39<Pdo26g3zy0wh52D8y8^xqk8`NJU^"
    b"v7Vq^VF=-&ML)Y!P3#zfP9N&^<ZCTBF0T_rYG=V^Z^~!FFZR>T`i|WrPb<WJrmx<t15B?eE7h==b~r6Ld{ZJ^4pPoNy-3NZ((BkK"
    b"e%Riy+?i_D186Q8YwVgvW$Gc;z6=>Ctdiy10G!MobGwfZINYKK<|QP-Z2QUjTr<;M)dB<N1j7E4H<X!U0E#Q84zhhv(3)AF#xl<="
    b"A~IUmL$Q$-`+UcSSX=fc4M;HRN@yFLAnFN)7s|&T@xPpAU8k&iG#}Sn%7s=|xY@E1wm(LHD-Rd?u7~dnarq2LSySOvQUyKbD<7$t"
    b"jn(Rh_cua#(7j1O<E3SAhCifPr4$Yd)3!hf4jN!XRU;2?Dzw{W`=?Glr%*H;Yw?-jtja>}ofc7GVLAP()>nGuw!ooPzcvBwKtP#e"
    b"8l({31${nrY^?gonK~I#v@&-8W)fNKJL5!wQ6#-N!B>3fR)5*@9i|QqY#jP!#voC3?my0yjDObgqt^*BCvAYztQ`x_BtBe`#qJ+>"
    b"6flP*mSB9=taX0h@-qfe^L6FQb#vWQs_OD~tWKz2Fy5Qz%t<&%5glXVwRbe^pOU3J3Z|HPvM9RMnl*&+DB-EEE6+bg@8+rw<<&0J"
    b"XDwhZ<<;hBGsl6-v34AI+B=f=r)G@%#N0FI1Sg52HRF`uvfM}4ocOwOos$-lsz9D6K4D4zcp=ZYBrS6s5622w?G-z02=Ct;xt?`G"
    b"CKOLuvxxPUb|1CJ<9c?ZeHG*1gz%8#hL|RgKa_U+xEOyeA=-wi?66I)%k2IIv1@Sr*FK@kngygsmM^3C>W-f+gqw9Y_8HedR{>^C"
    b"V>Nkm>(b^<kma$2;C!;{xp{S*^#)Mr8Si9FUDg~*pv+mRK%+TZEN#|r@`DocEAStHi_5dJ|2FskviJURQC(;L_;c>P%)RI^a}gUa"
    b"Ix-ivn%zy~5R48HnTuF8yGCuZ+nOJZS8*k6lQ?QNVnpT)ppcdbY0`!yL`a)9-R&>3Hi_A2xC0c(2Eis-V-g}4v5+)I1~JYc!#&?~"
    b"22@P5?dSE~{@HoGRGb;!_c`Z0=Q+=F&U4;R%3=4P8xI$E4lAx~LxJ3jNxBmZJ)6^zwm|}$(4At{3a9}TPQp5*i@BcJ-I>$WKZ_@E"
    b"sJ?oGj3upX9(AOu@0~YIT4~EYzT8L>N`4cYVM}7Ju7T4b9W-^ryqQxp^yk{k=8i1oj~~-(kY3M>4yR$}p<(A`n%!RTDD+3H2$J-F"
    b"SWKN*zjCz8{S_8x5v0HFmS<M=Uky)*Z+SSizp8v-H~zYK1%G9CNtFTppM6~J8gG53GV}kPJ?Bqeg_k?bKPjW&uk`Z&HL&I|R_(Z0"
    b"Y>No7Jovi*l|S$=zC0jFH^oFP-eVVaIHMs}HSqs8o|}ZCIix>^Q;3nX%ODo;jg9{oJPSqZmJY^%@B3ZO5`#DZ`Tk$<So|nl*?64z"
    b"Hhse#dL!yCJsX1sAD;F-**Qk4VFFK;XkXq2>^LS)jKuTT=w*O>!3!Ymy*H!ot}`+0`|P5xymMr*Li9D#@n}VV`t8_cyf1>I3s)M<"
    b"j=KALW7v&`eQjOQsv6GM*z?7Blk;R*)}oV!i$x&Dso4tIv_cxBz5e0^Uh<G{plf7dh2)D<IbBIg<im{BBMP5m`#0GCS@=1Q7oQDC"
    b"hqNij!zp-E5g?SY5E;9>s-*zSxHx|0mw6M4;)P6UTP6>rIZoJS(9U6<8FLah?e!anVCqlr|Ed=pv(nW+{zu{<jFUbdw*^R$fREil"
    b"bH-E8s)E<#1^d3J|4fuQbp0d0zCS|-@mvET^KiQ{K5`xWpC1ntU)oR%12^toV-yCTiZa4-;+*f~%~O-D<V`P^Cz~2Sk<A(#?`HAJ"
    b"R<ZgQW0FOH=7ynS?nM#s*P_W<&MyQ>8`p%6FCf|Y;=Fm46`aCsJRDT)Im5#D)MAHVlYjpME%5Vw-&sFSY}o?WMuhl_*6}}e_R+#S"
    b"g$gytA@uI&hoI;`%GOQvU&|LPzf-Oe>x=L(@&P<jpY1qeK9Mk_e*5PQ3(fJ7!{{%V^!OzSo~247Rzwf89dRectB3DbOMJHEm^xJa"
    b"wVxMOg;9LIwJ;?P$1}m)m&bL+pDYpA;6a$;<<vuB^}VPFoGHV_OY4iA<~Uya1Rjf{ViT<sC*ysg{!u(b^4D(O6u7u<)=+UC#WTk7"
    b"n!aHEUb@zBej%QMrNo9J(Gu3(HC!x~1S|}3JOloMeF2#&6uMT0BprDH{rl5%e@f1G-hTRFhp_EZ#khP1AGePlm~>q_`7f=w5+n6Q"
    b"(d<nhlS_5)4d;AthFB*r%lD@WrvI;S7%o3o11>?k$p*;7O{H&BH9?csw?FG_jj#EISGU&UpjhU>CZltX{q*s&u4ohO{T!o;4r00R"
    b"m*y`usfz)QEBV#z&SBUE+!`D8UmCkvc}MBbxg~$zc`-c9RYo`+{`x-0)f$|Cd;RV8x7XiZe|!Dy^|#mGUVnT2Z+i}3ZUA<3WCeDg"
    b"O{&9(sc-CLtRJ>b-g-L^@+zp!v12!kJP4i~u;suWuWh>l?D7uQcx;c;vuA{ZRki=^#5zK~0}aj3^_sd7L{;ggq_psbG%UJMXzM-v"
    b"pLRs5SHV3#3vWcD7r<i+IC6x-gFIuS!5&ZB8QvFGxd97u+mTUw-icW)!GaeD>Xp-g_Jh0BEK+I__JyHe*`Y`4S0HEg3Rvf}3<n|?"
    b"j3uq$JEd(OfIy2$@#MBJYBU#cZJnTXpq_)Lo%{3WQNR~tszN>B1Hd=yYi1sHVjtMljji*g9}6@*TEU6gv6VK|ce5ebAmfzb+1(!K"
    b"2tySH(~qh_<oE;NzknKD{m%WmDy%`zg?aF(JkB-qbU+PGoMH-|wsKUC7YSK4ERu2+gX|HZ1C&Ik0Yzn&JuGB!Q?brdr@s{(xv)aW"
    b"S+fi07<S<{@?1Iiqxqb~tLsb&;RSfMDJ8uS<oobyeQ${Xe4bs+2H1_9O?Nv)8Z?OD<MFL&t`w86R7=}bTP|N#YOWFS>qfG0n_=^="
    b"9}W*dN{znG%yz!ohwnQll}HdVu@oG`)TQsA2YXMenToG<osEW#=p6W5&@30FQapc&&12=lS4#~|Jd$I|6|1pc><SqlgF9ROx|#Ns"
    b"$X7z)eig44wsn-*_^6_cRrk-vMH=iZQJX6uxn`;ygIElPUyP=5&KeI?E^?&*Y}o7w@wLU9Zm7^y{Q$)q1ZVbwgL?6!yOQ1r+n`<("
    b"wso}t-@5^JgJFjl!rMzw2&2*(RK3iIMIrNbC3Tt;dr;-g{pk6fW{1fivE&;uo>OpOcCRtOQM@`maB>O7<G|FFg054ZJ)wtGp5h^j"
    b"mr>eg7^tr%RI|j4&4kQsB{gGbi3fGqeuT<)n(Zd+jme#O`TR|mYo!t9eBSK4bhom^g{p_k^mR2myLz@3N-v0|@TN^K0>~^q%^R@2"
    b"rf>EbaiP*?nDyQ*PJ!ZykE6=O({EsXP1t*!3(ZFt?K^1fxx~A@Mo)8OoD{M1^qhO8&1v18sH$1aP7U4Yu?y196K8}J&r>H`w}sQZ"
    b"=u|U)yCv$By#*b@<4`GqUD%vo36K!7rC*fJ!zmDze8W&|Zi<JBO|eF@6?P&c%oq8L?97fr7wPE|E_w`UWo9U*fc+58H=`gc1uY5t"
    b"pbjKK0GpjgiEV4M&SwonKS;_Z8dUQv^#}xARyOtfJCS)PU2_`U9w_V>J=C?28!<2>8)rpBYsL?&GR0d1<p8g%V4DeL8W_=YYqP_<"
    b"he4fQD3(#1fq077yGQj%x?7`or5XOcE!|77zk|>GU|-otxYS57?d2iUz=Z-x(+f3tWW>Y)inpoEa2i9cX(+0D+xvZuHM&Q$uLY#6"
    b"Z2BiWhvVfmIrmJ?TyLP%b#HQ5a%T*bT^I?cpJB%W-|uZrNeKpP!$SrgeeK6Zb4%@D%y)8PudklQ(c=DhW|W_{DMfj-&9*83^u#S3"
    b"IOfQkghCw@6i#8pis($aoM@mk0-d#WBX9Soglg(Xfj4RF%?}8rNjQsIPA4zc+cT=Yj`gm&&Drk0RgW75KT6tTpR>cWHVw9yZEx{p"
    b"ry4VQsYN|@CR+*f;u!~D2G7LaYu(8!LnR#Ovzl?4(_Wfn&XqvkC*_URc$A#|9Y<x6;w`VS7gRg!Q?`QefSX3)+xHh1diX^jW8H>2"
    b"vcuJ!^M;Kv2tIDL*>optP;3%xM;&0d;dXV?>UIzyZ%nbfEo>BlV}-X*^Rs}NRW4(NxdiYyiV8h2<0G+G3|0!BYH;50tr+UXd+Ka3"
    b"1?tisr{Bxy1gDLU<E06(VmlnF8iPYcV28qdO;<rf`{yy*1yn)t?7DXm%vuNeBBn+!EQ38xHILFzZzDY8E&-4-TESV$SI(`GOf+59"
    b"hS2C4p0^gRP#B&U6cso{1IR(`2xPrQUo5xZU0wiuCB*~ikZ91a0ftS_L(L4f4S@`hqfoh^7Eb5bAUA3+@(Tg-gi7(&?{|6%;3A|}"
    b"kMG#pIo&3>z!?)$rJX|jhH4oP=z6vTBi#qdl8rGg%RJWQ?ETrcRR^CtxOuJ3*jz*i#)@6h`o*Lpj9W(=-^Z}$f*_=T4a8(APl&U~"
    b"m}*)UrXc*_3O}6W1Py{V9%|B(YO>J)&I^{>XHmT40mEc?Hkq#gn+@_f9<o)Cv<b#2QD#XSHi{?sH_onP+jFLG429V~cCz52HiT>7"
    b"XZ!{`5Uy8R8oomW*pkXeSIl5{-z1xoXQRuI7p9y9VPE{PF<aOLm`gIjE<X5Z*e?Lmd?nso;M?*4m`4zXvc-8S35v=4?RZg%8DTYh"
    b"{`Kg#Isz3?G)mgn#r6aa#hR>TvE9S}1+aP^1Q^u-@kQ6UFH<L3d#|#oxyLG2J%2HIztgs+y#@D1K!Oxjv6>b6@R2q`L=q0To5wkM"
    b"Xn&?lq%SId5+RM&m93+K1Cu?M2a{fVS#IU2=hAYY8i6Pu29Ho7fgdzhkfH@vVRl|y6jumIt;#DmAtwWaYl7c`kfjGES3#O%uQNQh"
    b"<R@MnYAw3qLGA)SA^c;VSIMeAp13RRl5=0Wd`R-?xHvXIW1mcx?_PzE(pmZ3p-^j){lS~ga1&dgL!<Sd->DtwmQlmyJ;bS3_Oi+*"
    b"7dFlKXKIK{8$7=BDOB6?V3q*Cp4gfGFa2|Pj&egruNhZQ2`64flMC5Qn-!DlWg9dl^rBjG&8^cXwtV?h;fBxQxql0C?!Sih@q-b`"
    b"8HitY8;TtHhe^DHQ|~&<$lZ)PUhjZqc<3pdIIai7&O5Gd@lF|k?*nXv-o3*AHRJNfdzVfcj~S9C{tShiH@t8}5_r#3*fGxiHsrj@"
    b"<rbPUzBB#q5e;45Qw~?BT%mSaI7z-4poqf=LJfa73|n~F#AO>N${GFss(f#a<NfzM6)m}Z%u;w|x7wOiI4ic~^lIvxfVSup6-5Pe"
    b"Bks9e9%<vB;0=Co(?gflrRmZYJY(|tR^567PQnpVVmDE=b1CSffr;`>uUz?(_}2LEM(=<JE<dGw^fG%*<bNjN4UyaTdkT?a+3W+z"
    b"-ySnI4NS;4^~&>O?g_jYhNYKj3Pf@lZ}8p8HFp9j;L(xW!+kV>Jnt8kcqZCw-hZ_X?*E>^*5Od#a-WSlCfMj2CznMFk!r)U3HdVW"
    b"8zM*?c41?pna1B;IeiRoyo`6mcwwSGUyR~i#u=W37bMl2WnT5nZ9cpN#8D8q1ruWsxk_DkMZO~Aa`#0Sj`Ek8jv|xrc=CgrJTBR`"
    b"T$JWot5YCh;?Tn4imo)HlT7p<IdO95WtrXN^68t^HmR(Xn^fOan5}R_KmKm75#t3kG5A(O_myuwbp@~OWY)yT<^-WBxrW4$ohVNC"
    b"=49^Y*42~SO7Fn}_iy7LFdD<iL|-i-CnkRP(*DLcCDEYO6tE`V`_0fKb&k48zb~y6h7X*!5=#Lmakuye84*VR6tQPqbFAWR<iu=J"
    b"$FQT{r~S8Vj0}=}<a`?0ORNIY7^a52aa=0~{XUAv?FYWpDjLVTXS|QCq(Hn7Cm|!z9&&I(me>&ey)kBRr;^hXV)e9+PoB8)^af(*"
    b"vuzcC4uzvDf?T$pGb6siS8E4jiFJ{qgbWOJkM=f_>qOt^2wQr-vyDD%C)v|IgZz<yHeM{1wC^2c+#bGh^&9mA`XGo*_(;IIbc%0}"
    b"G!iSqDzsKSG$SzBMh1fc>l<-d270Wiq$k4kExM4rFE*0K9E#G`mQg<Z+IStj5Q%yKT~Lsjee1<wg%m^2jgf#=N1}IbB$hi8urie<"
    b"68#aQ7xB??e6!I<21m(YbR(&u&ls@cN57=EHLgM<<ol$b`cr3I(QWMf&i}{=`pJ>Oy*;&2X{nD`IRhk0f*s_u3oa5vrJcjpMzZwT"
    b"!74I%AwXuP{q!qs7F~?D4Z1)5pI!e>d@&@>AQ8JA%(aDXcE+twCFr?vzO|tr*O3x$q{kYe&kw)jCZh)GidY+JX#)?&d;b<H*BhjY"
    b"F&#yT!KkewtcQ;azR_M20&%=-F<2itdaM=rX#3BBH)aoxslby*-VtAW+dzSy$bmD?h_{mQU5|aod2|pR25y8M0{eo4)>>c%UKI!z"
    b"qtoz!y{+G)XWxJ*9ythnc<2npa}CB+aFW+fh_8hVw6tgVw-+1(g{%l*AU1_RI>;Xe$M6JREGK@#SnLc7$xV-R+M~7{JsVIu?Rknf"
    b"WPccV93W>Yo~6_IF|4uE%2$hMw|)t;(wE<(?QN#=onZ%cIpxG+j-s0`c$xcNG}@1Y?pUY1XD0rncCgq$qGipF*<jbvm?!2OF{il("
    b"cjj7-Ve8>7InSO;Q~Zd;rlkGhE7Y&CI^yP`e1yzSjoUeA19}m1EUD18skhQZbLr$f04`T7#{#^oG3MPwqAk;0WO(m?IU?4w={aLo"
    b"np(t@kEb{yW6e=)k01Wo$_a6~_x5ia!Olaq9;4Ht1orD@nV$PxoNUr~I(Hy?gtj;Q+S82#&S|v0ds;<eWj{#U>-O&M4?G)h?*Oqr"
    b"tR5kC$4cqjzV>D0lS;dPf1!z=4R5bbqL!bIZ`RO2+u0|PBwNPpPyMguHJ)>RU3}Gecn4n>TXw<mnRmuvJ&j<AKRUpZIZ^<txWk19"
    b"A9ioY@S9I)1hqB_!DE+Jh3ywqVEQ*!ydS=-F{))MUyj;nz}MX*ymzsaM3+72Ceazxg{fOHg~}JAF5zN!8G$P$muTGM{bmI?Q_dkA"
    b"?4p(@0jtt(IzM6o9H*d=wOzjo`(Wc!+I4Ba@fV+C{Wovv*tr?h`|U29;vh%ItZ}@dlJdp}+{gLoKkWp^(ve{UzuB-$O(^4py+0Wn"
    b"jFIEa8*^f97oC){^CZ5`P5i}HS|pY|Zz(zFJ_)woGRZ+L7sbn{VTY#W^zHU+$n${nnOA9ho3JM=TomPmdd9`ITBSP68?3$V<~B{7"
    b"PTL#!1|v2)<EAc(gvCYFzoNF0nZgassigYnKA(*QjZ15J=CD0@s^+H8q{E_&)Pbyx#ct9^`^cls9t`{FiVD-|cm!4tH%9lKaen5V"
    b"PR-sh(DC>*k5xp}3mHSpz{BoK2;7*DuFP4Iij|YMB%(_Uk3Mmtrj3Wm=R3K$2EW7P%c7=z?-3s>Py&!2m(R?mzJA=dEGNb8QH1jl"
    b"b#{xFq?XAoJEYl>HW{VI23aXt&;fZgir{OPC5ksVM2+2W_~;_vcxK5aiWea<R^sM~aXgFRq0+vn{{i1wP}9I}**Jve)(*yroM}Te"
    b"E%IvEXGpMOx_fXJcAgqAmmQ(@kEJkt7uy|?_=BNZP&z2yDK}&JM(N=|>wPBN=d%fR1?;~|pD3;PFm_f0Yp)?mK*xh%cVj4&{Y&3?"
    b"&e1;@b|;Cqm0Aa-DK6g#7NZEufl#xbGl~;i?5#5sH`NbhbujNeX3#kBO9Ot2w;=R{xU>g+!-q?(8*Yp&JIM?kR;az&Q`7CATMr+3"
    b"sKMFc9>X9kHc+FH;^A_`Q#&km6;S)fp6YjZg2MwoCLe7C)jvxQ44p*QqMQgB!5HqqtDR(UXRQ^DU!UPPx|EM8?HZSdf7Na%fX?LF"
    b"Mb9c5Qol7g?pSG(2X@g_XdG|Qik$s0I@OvNs2kk#;i=x&jG{C$(nD7!H)aJ0m_ComhISDJJL>2Y+$;0#d`*5%Uj4+<J)8}Gjp{a?"
    b"y<%`0do$J(6=P@O%RKdVwd}NU$B1AtNb$xjcT8<FA_#RZPvIT>j)7VPx-s=K^*#9^HZ&5)12k>I-`zHLW?cB@5s=5<GYRH{0Ohe_"
    b"_gUT4#M5p`FAYiDLv2SoIb=#@vqnGd-|0KHw;5xtd!Vtg1*FvXQ|{;rWUZp1^VzlAvN|tyJaP$U&Z=#Dse1qiFy9Pw_WkUV`;YK;"
    b"4svw}n+$B@SGGCAiD1GRXYt@g5;ztp1g!mv{HC#k;vJl^acmC>@PV->{wXkKbw|WYFlB~y;-#@qM8fcvm%l>w*+`544m<QzEN0l-"
    b"y236+hZ9`5L!WV92Guf*pO5TnY=<{`4`jGI^6s!G-aA|8jvkO5?n~N~FU@XEK4tL?&jaNHFS{?n)N)Y6X}T{cW+XKmoiJ0CGFH4F"
    b"`IkpOd#TRiG5o{B=Y0(C{gl?m_ge!A#CoUj;S=?alYvXx%#>{nuLKS_3Eti8gR(o1Q@pMs3C_Cmvp@`G8Xd=s950=;HJPZxNUyWB"
    b"`EZx_B-NMqw!c5Eb*|DH5XomTQ);~-t-(j-ODXWY5}{tq)36Y<eRrO8UrJy2a~j@f_nC@q(=f#|IneHx(~o^)=eN$~U)1MAeZNBS"
    b"l3g?X$z@wn&*Q{AlUeXJ%h^li`=0DNVMC^y&Q2AUm+>OCS56$Jp4w@k@$Z3oxyKA@y4M|Fy7xrpUF5r@VL|CHB3>q+Fmunp{Hoxk"
    b"ZC#|Z<@Rmw4rT+nl>7agPo4P9IUuBls_*h=_q^=>V}cWJZ&b2t!Q7f0YcY@Y2H!YrZ+CCo5yWCCse!7Bf<m8>XDN3M10w?*B){I$"
    b"LLIT!fsB;AIV2g*p3(rpx!HJrjPtlH^hmY8OhWCvxfOYh!edrmR}`H_)T!J5$}eMofVxi}Zm05Hr)-R!cyY?RqjVBRKD%^cDUDi2"
    b"N_xijygVAAvt8qhU_N=j)orCeQvG*jQ;XU~V>6(b)B&q_6JBLmP)24Y`4lyNvXtT3ydPMtnb7)Lmv#8bp_;aJ&-76|GM1Oa!Z-`K"
    b"V)!z7`UI8l#j}ZmR4fu>Ggr`A-+{`grHyG-(VNYV{OqOBSTR7yqsVsCH%C&t`aE5OBZ2bP2VU&gUn8HD)V;l-HB{{+W7-tgqWQ(A"
    b"bKGRpfo;bV{#XRgpqL}}o0Y8y3Iz+dk>RJEJMB5p^NUE0uQPW)_s!AwT14-e!H>xcJrBHmBMqQm4L<YkJtuzmI!`WW;LvQbOEh9y"
    b">qVfZP{VF;0d}T@dI1DdOUUiD**3?r)*ejd3!wuKe>0rgo>r(tjGnf(3L(ekq;BJ^YNd%g!jp>{6md3ce%)k+iiUiBbe?))H)fes"
    b"h~iNtf}317|BCnR==o%(<O`)9;J!J0&r|^#mUSFl_1TeWX&_oE%(~;d?=<&Pw;rfRUqUV!ZX)<?Jmj%Us$t8_FkI~dK*A%dD4vYI"
    b"U+UYj@sks@|59mt&tI2G@v=|lEE=krCXxvCTV{>U%55g)q&eHq@S0lPmsUn?c5qI0ht*MC&6h!2d_1Yd_X9sP$t!f;mw%4|lCRw*"
    b"DzAirZ#F#kN1C#Ay+j0_E@d;q%!RloP|vcuIKmj(5Oyq*CCBdHVP1DJqLZ|^gXxFmGTxNyQ}3w<h2qJ^lTna2Vb20$Wb2wL)?{6v"
    b"zkUH`@*me)eh?_$7?it5GrNv>!FjQ8A0FM|x{}+L4KSq$bGg3yjn6arKsK2y8g;tr4A;G!N9?)q5x~X^EYG&#$W9}<8n_sf&*5zG"
    b"a!ZEw1bp6Kxsn$lGwRRY^g3Nv>(lFzPu*C-@c5eDGr~gkebi$ZhDEwMM?B|CHN?BZl9m_yL8u;X0>s6Z%kE2yon?w`k<F-D5B>ut"
    b"??iFdTgI!0gC#u0i}xQdp(m+)>sPZY8q;;)+!iEYacWqBrdacP2LA&(xnml|<Lnequ>Z2Q8vNzGl@dGvmpAojCtt?PX3;0e>uLY)"
    b"fd@aW0Cz-+!767M6mDj3x6XV|TMT&jrNpoRwl%huP%Uj=F4;Y4i=!f|{)yt5rHyJ&yG+M}V|X^tYAFE+px~@zbBEc&<_vSx%^jQ-"
    b"uSCCiOlqd~Z%7F3-@v!>>ubNVu*TzY%ZvecU}s-H#Y2rPJ?(6KOXRq2Y@y2O)e7kH={^md%D06%yqxWamT{=bRz%;vlp8X_2d3T8"
    b"O6{oKH_{-bWb}-4xsQRWmj;9$%-V|?o-A(%q^E6cdq>LZ85tzQV{Z-tUSLsg!;;TOZAHr&9@bD1to_-BmArjtZikQ-EOhxRPOe{}"
    b"+EBWUtT>2QT*d<^3}Q7Y@Z|6HjChUbvF0IFd40SJly#&vrZGHD<15ix-^t~Nq~hL=)(vI4YkZGA0CN&Z%fa|~Xm7>wiuGWP`0kU("
    b"A=hAduMLM;>A|?WFf6sk>{S2qxaCvJ#H8C#Y93BA`-}~OHjOSWwDUG1ZYp{HZUgB0;rW4(5@vTqwbWVZ|7uF1F!MCN5*dOG+2eaU"
    b"LnYH<N|SrkGjr`ou)5`K$s^nDF>3XkY?thb&l9dpm_f=m7*uNvRi=3055V<+vKE-*X|#cx-wng+318>M2v-Dl_b8;T=sUdX7d?VU"
    b"ai-u(kD9M&qF)0o9V)M1K%U=#!SESeG8zsi7y;@?FBbv^CsPw1gfBfFmR6t^q?CCQ(M7IkxtHQS^t-+zVk?^NDaUS!zjd`qJ&*C6"
    b"YvkETE=p868V%lUJ|0F8XkpjKduXp==0HC(BYHVGo=>#2B2IOV)LTvZ;S}G8r)OqiQ7TMCAF*&kPEV#0z1~R9O9ldBh;`=U$EWat"
    b"rUZc7s-!6f)~5lKWrl#eK`zr|fp(2iBpKUAeqt-pGp6PJa~O6TycD(PGx~Z>jwhzmg>`#{!P|(@RR>R3PZa|1l!BJCL;@U7V%3uK"
    b"@P3u9<bYfYB1RG5s*zGCQFD0vSQrWn-VO-`QhYEfwd)NJ)rlR7!5(e6VWtcsd7rw?&f95>C&a6z@bI(}^pvtI@9vAIV+b{lV57u8"
    b"GvD{+n0-F*mC~C1{D$8#{nM`3c##l~Tp}+a?cfup$?{UtLLcV*u$<E>Z8CV&B=zKVSpEqJ9=#{BKgM%`k%lnmu;sT6R7{&M`LJ}?"
    b"k;_bpbXl6p@C?s7V(@LQX|lACw9%N!@rW^=B<ywV!}ng!Sa(Otifnc=@}KT<n{88HTd;0H2Leg<N_m0-E7^FoyUEypN`~6QvVL8U"
    b"hmCclo5odWje0s>>@$1%JVR=2NWOk~vMoq1+KS{vGV=Jz<*;9OxAYx&paT}XaeTA10wyX7R4*i>nQ6u*AL#<GFzfhpjimc}84@mf"
    b"#<T3b@|Vv}B;3<68|GrPXGYGNoU`A*u%$@d)3Lktwh<$q_ADa}km@6Si5qbVAzdC3&w86WH63~~2A?Du@j^KK)YIa1m|FT3FqPra"
    b"<(w|TT-pNC*VtH^IaqF>5bb}ta*F&M{g&29dK29xHoD%~0cLh{gmin7gYcEZl9s`a<V5rXWQ(VU3$w_1D1wdTQku^&_B&528L6pV"
    b"<v8h;%gM{KkWdmJwW+?6#PKZbnQ8O~<y8kjbcLOb2XzU~JT`IBTUkJc&XQgqIqwGCwLc}a9^@`#osqQS$CA;~AhrHVQfE{3TMO=P"
    b"YDwt&A-+#N7NXmcT{9l$wGQAsw)Bt}y>&APxw7geCpqd8k~gbhukUSlRv)bCI+$rVo5>hqM<YE};B*qP+Irm$O9=THRmfA`CB(vl"
    b"7FloX=Jm7U=#%?q(UJQ`<0o_Pnqk%v%n{l%&0PmUeQU-H6YgI2y2nVIeEVVs8SC=jgK1pZ$xe<uZW1$Q(D4+mrk`(^IIlu9tma}="
    b"Uy<z<oNrjD8gjFH?a{qW*Wis-!bZH2jD7T21*GX4Y4nyz0mR#{e8o9&t)C~Be_E9Gj7JsU?hT!y{j2dq#-?j>`xlb)2<n23<P!eM"
    b">fqvBLM|ybmXmO`B>nP<8WRb0`I2iEkl0G`_?<AaH&p3|l!K&dbTTXSM)C<b>!^{rP?_Wiz8q>K=M)F^5a24+MM29%d#NCDwU1a~"
    b"(L63GE=28Ps<W{?Fu7()BYD@3>Zm$@R^hIK6QKa<1F?)YD*eM4J4h)dUAz&f>l!6Ei40ShsfS$3Xju>rI=@^()lS`e7>=uGa`~=K"
    b"2Ru!en^#L#-pZfqAmlNOOhqK;ukQW7HU7^+@-cXO17xsiRXFT%e&yiiQazo{wY^VGIwv4R0{8)SCZ4Rn?g0P(n}i%T6^3<j+m-Kh"
    b"HBMBc=#~_U*H;p#KBwMx)&)b+IjA{Aj!(YIWl^b5E+8a3eJ&9`C?Mo+-KCh|jPes?<G$E~<4O2VQYp>U38~~?sOZ<*&v;=dc8eaK"
    b"G0-^~Z?q3kH<iWVpL<l;LnXNz#APZt$415R61_g+i{p8m)(rjtUDrKxOYJMQj^kb!j70;{C&iLU`TxFAI&bf;BV)lC^zEERGG_64"
    b"G<<iDja|7+wRT*-gedhsR*|TmU*>vX&HX-Db1)_a!X-(~SG%vcijgO^`N(jgoD{%PfSgx3gWE<-P7GY;`d>4C=&@fs?Hg8*&BN_g"
    b"`d8nO4{*R`4_x3x+TCM~0TL5Ohq88k417WhA>pVT!1!BKuM3gJ<;TRrl%ku-0Ev*XS8&%LIU7u2(|~u)2S2w=*?;RV*?x#(r*n`W"
    b"C1#-4-$i=E%FZy`ohqf)H0Y*%cRF5`1G~FO%txH2FXnbzyX#lCT~i0o<d(VkJ03Nl8a?)<j0diRT1lnR_4qmaVMavJMaZGa_fPmY"
    b"e$B^g-c;DNb{+0;pGBQlFD0hfc$rU3ZGp5hQBWO=S9gsJztzWE#N}*?KQ;Dys&(otD%nsJ>WF31`8L>2hKFOmi-R7qapzM->ZHod"
    b"3+m^}+;Hk~#~Ncs8Q+-$g2@yi>FOZY2CPp1>@-%5lUfmxx-_(XBNn)=G>>OVjE^cXiDO9tUbge{vW5mzDHDkU7R49-+pc`UcC*ha"
    b"vt23MCoaBvTV__2Mjb4onsmP<S)M05_-Vq<gZVML*yR9&`Sz3Wocr7(-n1($S&l<bT=}SYH*kyw6N)Cu=YJkJUS5&k>M}=6ryZI-"
    b"<9LC1@rTB+8!x<2IIHFg-rTDP^u_;<1sikfC*64yk}Frzcy%k^=jx4u=m1ZKQAqKwRylcM+Xa(vtO|`WpWjT&t1g^4bBpbLPAqe1"
    b"Dxl-n;MwN$cAGfbHzXvNziFn~j!@^|(@9lR6uYtIih@~4zN&1sVvrBkUt4H(y(S5pysjkycb`M<doz3hvl*Op6))29k(qRbH{VK`"
    b"gxAedeI5i(yB1H(p94H!w|uH;EGiN)z824lLiJSgh4TG3b*oefW>3B|cy@&(ZkdlTkx!49#)Tqx7;A;jq)Er63ARahGA-LAywFMH"
    b"CDhlSeC6+^BFUz!2p^LBzWt)HWp$=U%LO^%DqgGt#H)w9mRNli@6-3o_@K#MLo>4UEGLFlm*7b^A%F$A&;WTLFPkJ^B@}*e^=x-C"
    b"Ui1O5r}qih+y_f&=QhKT;BL?%*kxsNDcd0rUxR1BZ1)%ASqqqaa1B$BAaR%MvA{{#-WxoZvzEIqpPSFYZIkdWfY9^B?IoFPdhmXA"
    b"lKBzOf?4(YrdmFLsUbfHVxME{B)rJ0<UCHjTDNWz9{u;jGIl}&p2^qgrh~qhETDKb#7qidv5z;o$@)Uh!K74_;%nqPO7Wy5d<`wg"
    b"!6{n`PZiYiRW*C7#i#Z|ALyJjN!&G2mFXNAh0M#P8%KM_<qO0!ROp{F-n1j+8o%W`PM9^<ky*NNF2y_Q&q(pTYkxDRfa&wD*T(Z&"
    b"21#uCO5YdY#bZ<+^mi?W7r1h5dTuEmJ`IIs%}t$IDRnhmuIk3lBxDVamG;Ks^-Yt;>-h~{9*_7Bd*cNi+03Z1^-~jL#EIzWE48^S"
    b"9EBCp);ZWM*4F^9{sKc1I(2S)!1O&4S=w1tN}s;x)#29JqumjTw`_3i)Zjo?Par@(JFEk&7776Ml(eQh;&^v7S5XVE?{4vc(-!W4"
    b"sp&Ui_>{%mbTxXDO^~Ks^1tYdsp>4z*ao&on@Qhz0TrdRLvqLNT+*Hq-X`MP+IKf^t5=f5J+H+!0DNcmITBX$J|sO;W3kN9(W4Y^"
    b"*O9^CU^K9ucCD!cqJQlA)U$M@c{h%?hllHFcp-*8P$=RxS(Rv8J$h6mjWHUT`&pe7HIH-=-XF^t93DAG@frt%1L3`yOujoNm^s;E"
    b"g?=BmGkY);x^xX<v+%vE&`GboW-gYJ#8ZQG)h6ZQo~oFd8zBL@=FF~&w|DR0SjgZTZ)bSapG#uabioL9CF9(o!X?ZXx|{(1WM1n^"
    b"k&xZE7tk^~9{#^Go67h-2cDgy?P??x&&_ua+$&bk9^4x;#MjqG_B5JBfD+?bUZc^#@X7dmi>`)`?xx{IVKN`8yp9oTEWozetQ^S="
    b"OU7DQA(kvQ9y}C%CSD$oP;Xdg2`_jn@bT@l9(INq*O#SHcDk@YM^PE=4?A=asD-p8i928GUZ{#{;M}fgPHy)g;jw+GlN@FJmqkLR"
    b"HY4xD!9e{U;NvN5fiWFg;+|U|>clR`-@Op5nKoAA?<|CQngAKcoTRaPAr`ej*Kjl~w};~OkgTe4yjKU&pmlTZvvhn585b!<2w2l0"
    b"J099F(oxsCH=bu)scQ`FSsd>VIv&)=jwaB6tS5XhH_}M)nwC~s6Z0c<{`@l531%^%2pbPF#LAY(ecGs`7;Am%mRio?mc0jQ)JyFx"
    b"ogagKr^N+H*1@o)?K*lpA2z0zcK^XUJ|1D>)FMj{GQ5Fm(7#IYVAD9>hyzuao|b>@2I7{)G&vc|nm>tWX+S-*gY3q7aeO?^xxRCC"
    b"JR*Hvxn#7?EXFA3a-w2pJi(BRY(u5~)E3u!GI4XFQ%){Do?A%A<JE3w_uo6o;4ab1>mCg7VdZ<`u4m)p(G#)^XYRA-h*6B=r4$gU"
    b"oZ{(-s|)ST($dj|9ZG6ge8$GtmFb%mbcD{g#%@^7iDQEn#iJIAKM&t?k~)ePSxQ2dGAoxFK!dioK8{!IK5D;=SDqM6$4Vk3&f34="
    b"neyOL2kK<@na&T36(~=!SbN3uAi3l1rGJGip5#(1Nc%70BxA3&wCnxR@i-*Rh#wYUg|YVTUy%APPVKi<B%#hhzaL;(pD*g9<MHY#"
    b"=XscyaVkQ`!$ls-wKQIf?6D}G@OIqn8hV>1!~=-aI<+@cJ{u?q7D#QNqw9c;ho#5Ocz9u4K8EMMG9FfY)`Y%jg+79L!}#{=M!ezV"
    b"ZC;nsvO&g>YVt35TVXTu@Lv)4yxK#*uqzNT8?C$^vWK=;a0bShy&`lxI#BM1RG;bivUO%Os`<!xSWTW3^$pb8crdSMyb*J7`A!eN"
    b"jM^)9;$1)@2BBR=0u1k}zE~Z6F0m}eXofNh!k*uPCwl@f^#v$IMz&@vSBymCZU@Y*+77eDD+M4+0#+`o6L=o>Ij`cqw~sz#jJCJ_"
    b"q6ciTg3!`<V4p~0?IEln!`2<>a)#3RYP*^bJ0U@2E77~GWJnUBct<H7PM9R$?ZJ5e1@MY3)CWu$B-!KM0m~N_QqOo%EYN`l(%byu"
    b"oZRRxoRGvaZrUiGl}utNaI}ZYmykdr6Z6-)ozLAB#}nh;y;T;Db7RaPmoyL*!Id1-jc_FWGZ*B9%6lslq>lcbuVo$>*on81VRR_9"
    b"lRvN0HwSJJtM6_p$hE%C=kCmU6$kK*aXf9%^lq={YjBgZm{tC@r^fuorM~pxN``0H6QoZc+Ud<K8`y)L6fbh;ule)-1nF1-)xSI6"
    b"-Ii-L@wt0a|DEDxj~_)u!MnXC(y)<Sz)%K4FtyCz(Y6F^Dx{a9R!FdWWVM6*p^wxxlEK`1P2|I7f*{5Yh}AleLe_GWdl)RW7{_Co"
    b"RccrvTO&SbB>Pn-oguv)MuuVJgV>;`4<G{)9EZO3{qAGChOL|cc@(|$a3dd<6NFcurv3Mw2XBevJ^jP2dNJ)kDq&9;l1P6+j*Spd"
    b"ohITs><q6DBtNGTq(Xw^Nyd)uA{3*3#iL*K!(1^e3y!%8m2a~QxeQN%H5AXKGk#G&tRrW4<goo#ovxjH*S_)>4;luvf6Xbq0<b?R"
    b"@zZapOS7I`<-Uu=ZoPl-u3w5_NJwnS_t5cpXB)Cs@XNpZ(o?kmTq-0L-Q$OWz}b`38pK{donc0ZnBKAdkjFryr+l!4dBKu-0=!wZ"
    b";=(71m34n9UEnF+)K51rruN`?LC|X9m*;0ZRUg3Y&V=s9Xn+izq<&8HAb56l-Bgg?aW8*UCVBb(Ax@M)NsxZ?ROLul-v)OZ85IM+"
    b"a(L)`OAs=kNvzIGsLiE#dD5DEs(*eLxVy7y_mM~qHPu5Hd6p!d?VtTYRBX;@mXe?2L<GqR_QtVaKGK<gM`Vzku?2oL|0u(=y>jOX"
    b"ikI<ph~nk`$NRcQ+iUQ}mEfkD|3_wxE@0G9AG5Wj-8J-r=?vPpt0-~5rY6|=k*dKe(?8rp&f4}u$-l+rQ&U^T>gAy3S<`3bfg32^"
    b"-Myv$bMgFFi}_>*UiPw9WIMBUb>EA++jr0V{$g*)q*Gzp#mr3^_?#IazvKe1?D-wVOA>ziT{<33E!&!{=Tn#GAEN6UDlz$J7@cBJ"
    b"%x0>=&|+A$;7lR)o3*6S@IaDvQ;whF-O#^4e-Zbqg@Jb4-yhn&PrLw0QbPXAVm0pAR%$)(UY?(+R2TCH!`uuLjSfdFCZu&Az+yQ3"
    b"KT6?h6VM|qzyC#2mp{iNB}jZ$)yUf1G^yBHKi?^cK=GUsU&D!yHG6*<vh<wgQim=Vi_e~0*H}s&ud!1i?ZYvu+>4XmGEP3cTIcwn"
    b"aqsr7X&e~vnSIah1Hz5@cS^p!n0F>^d`ToYDjj<Ng!tGe-d_i;pWl*~^Wk^b2V?{(etY1*H;x%BWa(zJ@BZI8rq~B)oXDG7?+D1e"
    b"gfo*QKa0v}pyFNzd?q@N#33>)I9*ges`eq`ZfsIOmjm=$OB0<mJgyB6(6!LcPG;>}G90O!+CW%ku0U>%uc+}SN!=?KbBf)9b;FqV"
    b"4PE*z{|@><_|+;ZA3px=TvFK5I`?ZJGx@F;s}6Pc)UphNk@#*}(ntOqQ{8nk@OiBY6eI`RAxX)$&Ef4_ldvj+k<b6o&HOOwn_}nJ"
    b"Q~5wz&KY7W4SUr9@aUsGk>PbcnC)wh#Mz-&CaVGzR7I&P#8-w3WNKd?m41?2#+UFlaJvNwK93&s`2w+6KD;Hq+6=JKOUUlkEn0m5"
    b"mZPxmZQrPc5Nq!EDbQ59mKRhSC`aI*2ycDbBdCu`CFqx;!Qc74J4PTO;Nf0kcJuoDDJR5N4fy+e*ngDY>D2z^m1-&P<~)246K}LJ"
    b"?vdxXkg4dE)K$`R7QxoX{n`35iG8A$X#k^PJ}^PI!uHM?9y57haxy!1<_;KvnB}wLc;0y8SavLUM$k(+{>Fh8JHPo!RlIPsy^P}$"
    b">%ZEMPwfqJfqlz|*p6EmaW?TqcAm-b@-whj%yz84Svz1AYtqCvi~wE}975TA5FHVqcsEHP>|<WB{g>)Wm{rulQTc)_fHc$Tnoh@q"
    b"P5hp)o{SL1OMzW=)Hlhyyve~EKqH)EWm`3yBZCGun{T4e_^O0Jx-mzYSz6$>Yy`=b{NL~V;JS2BsJ_rKy?gn;$xnA8#sHcvoQg~*"
    b"t&_N762xA6QrSb=lLD+R(veSmOiq%3mp8f;nJ=h2Deh%>73qo%fh<0bSAc+I0ctum(W3FbaA(1yt^@K_Jkge0{``uE%rwv>MNcHY"
    b"YC8342i29Y2CTTxp?D>Ox9GBhf(`2)n`oH4*=6G`J~<lS8n{yYlK&}i-rQ1CqTLLJqU$!rI}?)Zc4P!z*5pU-D2<54E%)3ECup~<"
    b"Y%zR~g#ePVA?V+c1*Zkc^=ZSk1H%zl=hlph6%<b~AeM{6sr0e;@X;;0Elrj&ldm+;z(N5262CR>+EJHtihzC96T4r!t|}CdS5t@U"
    b"1~Lbq=zJ)nw$)!{q_*K`UbW(vP1uk(P_K%6<wVwAltA97Zhb_aP97*|(1QP%Y|PpagpxqDaa?MF6CSE4YMq7a%&Z<3yGP<>kz>Tz"
    b"(^MGC`>|SHdm3QH7QQ-ZlWeDWm=j5Fy(j6;ACV{OlfNGP<8}L{-t&EpC)NM`R?hF><p#L3Lkn2o!Xu~7KigR_u=J_Uomm|_joma<"
    b"ecG<WdO-HCo^_;2p`~^@f5DMLE|_wh;H`Rn+)0r((8YyR8yfX7+GtdDcWJ=VX5mpQLP+1h=m;ygHjJaWc=R#9$<t8Vk$cXrQalMB"
    b"wbv^P$;FTC&U=o!FSbwJc=X<PTW5ZzFBeI5GuR$0z5TcFjYWu9ki*{+IWn-P_QTGC%-VB1Dn*L7v@yAVT0>3PnZMt_?LTdx>$x4|"
    b"jU=);!GI+9$6M))S=~}HMFTs<3jv49sl2T=iidwIZYH&nJ>6rS1xsts?F{o#t$Zg*=~oZS;1q*qP<p`=$4hS{!xh2pJIchd4D|If"
    b"PR0g2=W){Z0=Hf=DnOae6D!!AI6{Vx4n`tb&z_6C))`(9)x=HF6!RaBc)(F`uURVnv_V%B1Zbk2Vbiv6u5?C6c(`G6GRBah`^e)|"
    b"U%sZ`3i!I$O-6Bb>e#uR&vx#lc%6}~&ajW-nT6SM_ReInzjez_5u6HElLT7=A#X<3%OLXB&yDy2St($nkvu+rLPq~q*O8$&<!kx<"
    b"a9z}>GOZg@tB%WJpRpy=$x=?~(k)FT<h_x1X06;QksF~oxu!MUK#xMe%8cgW)(oXG6AT|Ym#uw{$SV*voQ7q0HbJs28H6{TfR<v4"
    b"Codu7#UJ};JyjX8s_@*@+SZKKp<`meYK#_Cv}SrMcctP+Vl06#z|&&e+L|P|2;#9f31lQ-XOg7$5X(&0SmWHU;Hmx20J~s9!&_44"
    b">taV=!5Hmf*m^CVC6MR}hgR%&Hzh8=*x?K{t%US8k0(je8(GS2oE6)>&$xP`Iox<<cbKW)=Fj2LcoporfAAKAhB?PO67gEJsoazk"
    b"5<&s$%W=+lkWzW(>WO9~a0PEFi5*^kEnQkHh2lwJzETW<Vl%=H)EHc?HPHA71<0@ttQIBk{pYWqXtrG?#ihZ}_VBgC8+OL=dIf$E"
    b"Y~tL#=TZ-0CF?Nt?>RyvSx>wi3qSbcRdTkjA5CIvJ0CWDe~OnBt`>|30PvEr;aNM!o(Ek>kf;ND98gxAGhFfVSI*mfuUtJEA?LO?"
    b"sGq0NGz(q#$+DfLpD%fLq?C`*HP`sEGJ}wMK;s;VF~?O2)X5j!+EO=vj?yAPKGHmys$|!ESYC1wK51@JymbD`>j=>RDQqbhKNT)>"
    b"o|33>zj>8uF+JG$CwN%jUfU!GL)d+bN1MMhSot(vI}$uThBvp$M^{*J%>D8NX&%LMUd9u9EFFuX@aG8hG)T5{-aCSdN6pA>%?x&c"
    b"Xm3hTeQf_=?m^}Wh%xu&6PU)Rw(W|10jm&x?T+J%VNC|N#r6+8-~z7D4>G73u~la9EQl4YLTiA;RBoPf1JwtEbF`76xVrk0>X)uu"
    b"DT{f<*3Y-sqR|#`{xC1&c^+fH#5cg!L{!$nZWCNL5ArdfLr=?Iy81Y%BDa3(Se(N+G#Lx&D<jyp@^g5;Sf6o2nEOMNT&G_Q<o-58"
    b"u!Aauh4&cqplIrWfVI?$0`Ch4V!3_9_y~$@f$(^#<M%FsCuP!Uar}<YrTVq^rJA1Aot`vXafv@&vg2=Khwvn;2Cw%SPB$`(3xNw5"
    b")Z$SGp^_Dx0mz^+C5PInoS)|synz4lK1KJep;539d)kkpcHB-w_62mH5Ow%OmtA0~@N2aA9dEuPUZDfhsWXunq|-W!9iiz?4AOZL"
    b"<3l40KZ5U9E1Rl27+&;ge~{rJ5Zb8iKsD6oSL_lu&L|CODl34*X{F#$L2|n0S|aw|+DD=!N_D0YS%XpM!0%C2wSsEeJGX;iREG8P"
    b"4$P{L`q;oPGg@rQ<vYHqu)xKo0dgfaIlS>9p;OJ}Lgf;x=K-RRUB}?7P8+vIt3lOl@pkx?=^c0mj;oj_E!`-C<lgqUkBuyx6W82m"
    b"(S?8nKI%1kLAd(?i<OLJNg})jDj$x{)7ZX=s-+=gXg*bgmAFzyGP>xYP0PklXqzv~S7lfM;vSpP4n-6X!XB7w*;WXSx~8}pV5N<E"
    b"qQZ!*>A>VeV9Y_VtTb3byIx7YE}XT0?YtE@I)^r1lalXB8op{sVTtP)RXqRgbfnN0zSgq?ypXO@&)I&c3~y1YA;KoSCmH+7P#ljX"
    b"blD8=8H~{*s;Wr`(<15dO9<3>(K%H!YunE?@KYx>g+@d!4?FNtTR3LBRJ_Iu=ttDYK;BftC!jY<@%VB13S(&uaA_5*3GG@Ex|V}<"
    b"o7azUGK}LXGUH?vI1eLg#A}LpH!EMwsi--p6n|Wb)pizJtkf1<grMaFry;tJr(HX(>K_2UGWjr8nsU4@ibmCdI>q{SYL&MLJdRdU"
    b"yW|z&ft9XyRWBE4bWN3c3w>agdqG!;+lqX?y7@wCpLZWIl-^4a!Yc&ZZiNwurg>~ATn<_^X7h)sR^4dNX;*aWzc<H%(h=t9`O@f|"
    b"nEofMtH4tekx7k3FbqbiAetkrC^uZ^hfswA=+u2>yU~0BvJV$ZE?s5*JYNx`fd)<j?S_g#%jG3wVaBsv<9wQ7P-x`C<1mCu1*eJ2"
    b"(?AjCzJU>qf$>xq&VmJJz!Rl-TRmIOP*pF@W_Sp8_u4(?IPtAuvJ0~D>@GX?UFX;<7~yZIZjtje*G3(7NB*(LiWg}JkGu}(KOraE"
    b"NW5Urqxwaglix^(z`%SkKUU1-RUHDX9B1J7VedbKf3`ZCX@bXodUu)Ezr;Pmq{IG3#sxhqh%>rDF)_-<&K*F5gojWp`|QpNFtlLv"
    b"&`rfF4uccB$p{~^+Q-*#lYegsz~3E4ELpGyl_~j+SmIdZrpw{cAS>cThXHaV=UN#Ij-^MuS-p<Qw>zl5upb<v;U=*IfxZ~e)-_C>"
    b"qsOt4y5BKR1l8pC$#kYxAPo9V?cmvi(tmM1C>m%^iN8|@FCXMU2<@-IG$!$D{0}9%bPr=6|HIzbBhf(r*y+8PC&vvVz0+eCRUz7!"
    b"0Ch$^_q7Tr%rudAKd4qXepd@5j(OVrhZGNNHyJE~ZlxYJ1aNBjHv<XywUL2POWTx~H`w<xKcsj5Yn*(;L{J0uTrpMZl^Qy{5(V##"
    b"<54TCa8&13o<rtW1zWmK@wPWHW&*si?b!{lpt4i+op2ss8eDdA$mI0YOU#+rZYH}hgi2He8J&<?L)Y1@o`8Wt6PyS4P=n42#jJ2q"
    b"JkbO_JcBCK^W<<})R*{B%{yrGk1vJ7rlbGcp<(mJuYYaC*&98Z3YAK8U%JFGb_sTjdA4w@m6fBnrM*f2alf`0R@I_~8ZvD#bjkyX"
    b"LxIeK!hqOVqJr@4^D~=kcAJYfsRpbycxNaYj<YQ+3EFK>gB=`<qk4<RT*q9Il_Ntdg&}Ef?e<5hbT-Jkn;CoESk~2*_tHsfjZa@X"
    b"+5Hl~?@nrxJhMz;mJz=r04NdLzq)}o-)RoXvX&S3V9{w5G*I!v4D5BGDpQ4(IjPh%IDf7Pi9hghRng<XugsnAL`eVEE;<rE!|pTu"
    b"tYD6Z+U)6DYA%B5G<d~6o)eP}o3kjM=RYz^Dc%CARNu~-PJ`sskGFpJ9xcK4R45Fo3qlVZ`lYBZt_#u_5xab?5?zdGkl{hoH><7o"
    b"sE5s(cz$nkQ}XHE;!UvjGn{Uo)8`8Ch5@1s$hRkdIH$#dkI;BdDloYOLsZ;%81oEnL;~#$wGDO&@hJ0$2Iekp!kb@LSxGQR_M;la"
    b"tA$*tmHuP7t5mR|Af8G4T6*`f+EMgquzi?@I=CtNSU>utFldPF%t)-*0)9TnK5H1dXfK)%Z^Ap=0x%tsVc;yQdgQF!p+4tv@!&wu"
    b"F}#GYKl!R_B)2<n{h9SJb%R$ayNF(Ypb3Lf1ae943Q+h0iSJ9Jc*)_rOt9>WsQpkN`D=roq^Sz5EM(-hwKPaWKPle>kT`gFv~dVo"
    b"&EFhsKvNr*x2oIUaPj#psTXPtgk`~gzaj42d#udw@$oUyg1PaC1^rtW!}Dt82t>V`+FA6I+vsqJ9p0gV_Rz1*Z;~1mJpWef&3Bc-"
    b"?&r?ZS?R1bkeMymbB=R+_I6;MQ$?_mIDrpB{6n|4+eay03aX_Zi`!&7d~~30{BZa1Kt=9v%vEGPs<Aq48FRPr(#Z~vvEYD1j|oza"
    b"H#uOhgn?ElhZRFcnJu*f9K2^c!vie<E@Y|VMcNBDQ8Tu-hg3b3wmH!IO1}q`WeaP{s#T~cq@O$tYv_D%3R93Li*`5YcI`Cuwi(qZ"
    b"?y`h);<e&oOSlM~RaseL=_6{9e`q7WDO%Xt^W3cd21q%2L;A620siYgZ+u&#(B^qOCb)!R9uf^Y1v$v_s)`VuLqCpY#b|GtamwTl"
    b"inkI~u(`R$L0yyLe+<;mpz~wq)@KGhuIvQ3u7*yoFnDA*9u|1$)P1=X5-T?8%}AH{gw53ZT$5uLV4eys6i-o8seJb5srohf3P^ZI"
    b"C24S;J`UVKc-75YUAA9;umR*aTXR`hfdv!~=@gFo5xajoQ*Rb_AnM!Y2o9TS1I-1ny?zJ;o|VglhxQKi{OEOgTX@C?>p?sc8pv2M"
    b"FTMZ6pMf{NJjFh8(SbS0h5XWjlf5;C_q8bZ-e>FpB*8}9x;V}uoro2>NOH4g)83r+{nrY5+%9cfSjsF`#b<=ywIsR!Z6^PYA&pbY"
    b"NQ|}lacUJj)PMQa-1~qwO$#%;J1R!vu_>2`*@yj}yQu-5@zj45&;?=cLgTi)c2+m+s~!Fq9)0G$Hw|YnUXPSIE;-b=^Bi5V<zH=b"
    b"K~@sWK&N;c@YE55st_mfWgZaw(|=FDyv}#7MBHYb-FE!DrF1|O4XyRo=3otcW=MQoKE!rt4JuzYU|Udi!9lRo;18sbr>0=ILEWq;"
    b";A|Us#Ew;L-uyj$R`=t3kABqP+HmGyFl5|(IJ2~OUDMj*wD;s(fv&GCKe!$=(F;R1It8SI57L#GI@BX-je}a6&FUYXY@&D|{3FXI"
    b"zJ3Q)?0?b|U#guQMzydovnJ!2*o=yAFomXyAZg+;ysU`2iBx!-EgPT~EityxJ~c+>-%G_`&;oy`Yf7+FZ!Mm!>OJre7arsrFC4Zn"
    b"(moy{1H}7y)5wQsv?JBb9rfHNi^t6DBGq#%ZH$9m-#Do8#tQm_5qjWW`nUy^kbof=Ta*Icc(Ovz{lDm_s!wdN&y|D2hF8n68zge+"
    b"O9x#HPrWFMy(XQ?o;7S_m`{JB9zTPm-LbMLIMj@6Bh`|>S+E^*KNU~CzVP$hnxAR2T5bRv|A0scub|H5{3E4PsDlE06QF$4K|K~b"
    b"6-g5{)uA9$EfiUKTbrHLAwZ}a{7r(ZVjIiV7o2V0JwxTkmsT#Cm9}PfId+#exOxAkSljb4I=V6|2B6Q`nI6_{)Pu2U>5LgFH!2GM"
    b"A7O6;A4PTUk3VN-vNM5AW&#KkS#~Et0e_-w2!)M=-3d^k_gcZ*-m0zFEP`Nftt_GtBxGkvOt1|kt+ovnNPM}a_f0_B3KiH1iAk&>"
    b"iM3T!Bol&(UV&@~l1+9q=YP)ZCPd4<e?A{SiId&$oR{Z3Z|8ZTIm@&QFPR3xQ@PZbVR;+wyYru?#ml0b?LWwPaeug6jC{})nlw)4"
    b"dwzb-Z$)<^h76(_6oMzox{WU3TN<(FUE^d?W%6i$j7fwo*9=?TVZp2ZQ~mCpz4g*|XrHnA+C1ZFtkpywX0g_XcYzgO$}l>a83D@G"
    b"L!j3aJCgCI5T5FzX*OIkp{^}y8S#}{@mtStSbS|NSB}HcRk(*no1<>GvbmhHA1mBUr|sJeKsw^+*3zU#Kn)&sw4gi)Bcb!`f$r8N"
    b"HS-2=2gKRoXa>Fn3^DZC$|yCo5?$Rmg2xixi|P<(RT+y?6h*cc3_%6qs?04T)uaC9Rc5L#|05o5o<fXp$ue8X($6J|rG$=-bXf?%"
    b"GYULM@T@?NsE-@#ii+b?=SJIyAy*C74zI#-H%st}TqbKQq({T<Yp?9+2)}p6xE<i>FTQT7TP8SrEeTR*e6>G=s~nqoR<8(vX&-8^"
    b"qLMu0h^<`94s(lDc#^X-S|Ny|4VKxj87((lNml%@G-Ea8NiJ$Gu#x=GZLgDg?bi(#j&_>IwUBm`qWL%e*`6_)NB<|$cCJn*JcQn%"
    b"2Fb{^I$)nsfk92=f0*oT+RtC>{=e|};xE45XF$`Efxq1nIYhSkcW>UW1LqF~h<UdEkLZoY|Fc&9`GYq+afzNMhez7SAR1ipQ_s{z"
    b"HB^U}hsXd?TR!`tezRr<BX}*e%0x0!+8QbC9H5URdqjYb{_uj2%ykJ>Pf@)8v}c<7f8dP`x<+d9-fE1eQwJ%%aq}96JdWsuj4v!c"
    b"`ge2u3SM*i*ZxYIn2vrz^a89{)vu({Hi?Zca+qcf{9T`euQ>ABZfqB$jiig-cq1{y`P_Iz+IvI?Ye^?uX4%2N^E{DLIFT9I>-1Es"
    b"7s5R>{e}iBfepqsm=uYnDz>f@u4+*7o9D?%7ryoN36(&CJpo?`tidLSPaO^6vwu$j#TqQWcm4byQ!cfcIx$xyCy`v|Z5l%9qlvHt"
    b"Z$2c-91?~f$@_aeeh7G{P{9%{rTf9{WRE|k^k>sia+kTUbe?4+)D+Ybye(yib`uJHhV01xGi+7_GR}p~QphOwScUfV5j=ttN5>@8"
    b"PMZnEGL!6pyai?6jN(~?(BY|ImyQl>ztZOMGyGZVWf1il8ddH~uKB-`*)wpXu%5sgiG^gw_R`>qekUFFPXeY2zNL^qte|1IW6GSF"
    b"ulzuFxoD0?{A`8a8Avt?5rEmDCC|17V?v3=vye&a=Dj0YEl$?E*96u^KBvVqq6Y}YpQ+b^br8@1_vm&%iu`p<MDtDmr3^~X&{wXs"
    b"mL<ouHb8O3X~ktRBF3t3tU9~z$~aBn=o;<PEIiKt|64s8P4EL-;lJ5=Lwm7@{vo}PKAfcdF9=_I&X99F25&6AtWD3Qd+<%GTkE9%"
    b"2NDt*R3*u5gfV`$uQSl>F{E{)^df9<-9{yA*Q4~$ll)`fsQ#}LCTtcaYX946L<B$`7In^Cotzu`zvulm27}}qEYBCMERSn!VOQeg"
    b"Gj24FnLhR_Nd)%|To1fJY1-oI!O;q8*!<H^U?cASIQoBev~=P6oPj4-{rrzS1Q_3Wuq~$H>mz~o*zBqgnv*rT4-dQ6b}#n&daw0h"
    b"`NnA+GvCAnwWvqnR<g-^BaHj<Xw;zO+oUr=TB1USfhc1wIJ>rcew`1S9eu*sd5vSgf~O?q0-4lcy~*R4n}51QpsD}X`)MvdnM5KX"
    b"2c1SPd^wogQhezKZH}|)V@WGHGr!BoBt`~ihmV-F(5gnyIni;jCmt^}Ynrg`TPM$WAG`2J*f(qYf9YfJD6yO;rp3;z1fHo3Heplb"
    b"K+Ggd_NM6;&&2N$x5lxqlp8oGn&3vB4Jn_zzBRVL2LCns^i(2L+MY`i)i|m-rNol$zY?5I(<Zh=HloEBN-+PXq2>5gZ?G49Lmc4?"
    b"Nd>DXJlwzKKX0$W$3L6+4q+gb9p@6lX<X_T5~T4y;K<pQ(2U?2vBTxYXM3+>V|WY3HL<N@cwS5&dve6U2Y9f)v#w@>uZ`eYD#Exl"
    b"d<=4$KF~O8gI;5gZ|aRk@!n${ZKsEe*m<>IWw;|rJUuz_N3##%n();#(e926UmFpgTejv9ybLVC26M<de+=_@^qh|5J^uB;EsuxJ"
    b"40pUTdu&nAiz7!*?uhQl{#Csgez_!ib=6c?8(Hct|D5x>e;fz`v_!;!l_F%j1FzN)?16Ov%Zs1`uX@d+-%LM1zTwGN7M^n9p32xn"
    b"UzIDFjbncIF3KVo7G6uVT4G#y_p$olVA$<33yMzGn8AZ({+sD*{NmUP|KTeS<AasE_s=-(YU?12ySMF1|0^#LtuMP5J7|On2wP+C"
    b")(pqy7o2xpy}0ahSPZ{nQ*Jgsa%#Ff%LZ!jZ>RBRw*I+*mgfBP$uD~QkL*8zFK#_0dJ}D)bMW6ZlyTla*dgB??|dWp>*}vGl7pH="
    b"1`o#B&0R8lqX56=-0^CS?iwvs*=P3Fbha2`;_hO6PVZkeKzr82t`l*9er@i4&<d?7A1Sdqb}<<@SA+MQieG!NLF|f+)*(F<?mhBA"
    b"+GT1;!?+Xi1-0oF>Vw<OwUgIAdcdgpYVT;;<#9coNG{%2cwXT}d{4oNtxa#Q=o%T{Aifg(`0C`gh)yRw?#;qH?Qx=<Tg3#?{(T+k"
    b"A6kD{N%w2wm+9}|Vbh0eA^}%Lw2-lN_ZAdSTJeGL-JVfAvj;!_hZ;P*Z1}@Q82@J5tN3{z-gf-GljLu2h(C6`7agv_K|P4K#;bzn"
    b"J9XIa7aiU}StH|S;N{*T^S15cMgHHeY#o{JK=4qmcbWOhz=N&p#~&%NmMHWE-3D}uUAxFFiW>C0bc9R5&ows^^C!RBMLx8J=r*y%"
    b")t4Tu@A-0T=g9cJG+Tp}?_Y$;n}RroV~fy-he~Y*GthjI*k3j1%Cf_dX3QMGO{Rm563d6GjI>d@QnrZ$+uraCLqDnS8(i~ctRox?"
    b"_XdZfri{CK>zwR;7;hi`Xpz=Omm3jLZCBCJk_Mv+?1<_^NhWM#RC`k6(Nsvo-;5s0!G-LXqsd_8zit27ivRt0GzDpBnm+hq?08Ls"
    b"4drU=&);dfbe5b6>0-7%Dj<NbAbf!;hN=oS^XcfU;FqzCFB9^`!ZR~g)MCR<Ior@Zoqf-)Qy<&$<dk7wymJ?>5UBcNY|=;iqbZ4k"
    b"$u`<kR)zH7(~<SxGLI8HazX}(3P<r~-zm05Y{BE7;A@V)%b+YMr%EK5^|{J>h^W+9NLL}5aJHV}S@ka{9wTPA6mJ?j@$ul8glh9j"
    b"#lAk%M#ne!c<^l%CX_>&YhN&k9%)<B073%KNXRNz6#QVBVVa<7!i75yeE;h8;D>{YKS`up(ed5Bcx(6+>+2oB(LFOhKDdhp8oDTF"
    b"fA>u8I-)c;gU!y?CYMhW=pd<-kQW2r^=L)s@qt5lbbQeuHg_!E-Zn6SR`eZg3V%#r5lPlBVF#at&C%vis0ALjv>arBEW&!hx^p=N"
    b"tmj{M;~j%xax9X9WjKiAcLn~!1!+L6Idragg|+2G5}I@jtedRkx5KCu?zV^o?Uda*L_8iU9SCT}hMI5gh=u90CGyqcWPH;%eKxgx"
    b"O=S>AiWlQJ5Ay0JMxoXL7H;`W0G0`d5K(d@dWIzr!Mp15fZajy8hc-xa_;(U93K%Z1TTKF?}xYlA<~MAX{-SgB+9YRDr&6jgx&=^"
    b"TY|MxBG4yOJa>-X0JA(%#Je;iqGt@ObroGFlNrGy^BsQli}#;88|l$^;479&gbgxOxzd`#Z|ruy16Lq7GNv>G!%bgA@TA;hcMDeX"
    b"#q@!H-g#oE0Gp=<68lTn@3D_7#V-nHYuj;`rcy~@CepMmDibtY9G`~Vo&G5_fP{CGb%?-~yPZy1WwO|Tf^9`ZYc-n87fXyU9FMg<"
    b"bpO2LIcO`5{lGyzAs`6H<_3vHsqL}nNe}`5Y`Uks+eYzLm!+r6>Lb#vJ&u356xA8fZ|tx6kLQ2ztJ^=?q+JCF){N9xw_8;X&<ju*"
    b"Sp~{!qUT#qt@MgAAdFA4A?JAYR(Zm}=A(bTo<{{$&<w_gJIE%-3&!QW|F5kXT0gcTenyl>j-9n4Cl4y!O;Zg;F)YQ7ji!}@dpaXI"
    b"-*${Q9+6>yoiJ&LhLylm#dQ71#>5|X=DfeLC0E~S6{I$-BIV2Q70cJP8V<SZr2815V}_eZUu}gd@zSHjdKMH|?+5P7ao%r5gPL_1"
    b"gM>E|JoDjO{`LCzAHD~efO9TOOgJ!9P}f?Ei51<CL>f<1xG_{HX<Cz>1E@!nIZ$X2NcxutzOy5GM*?pb?!l)B;S>}+^2opZaR3k2"
    b"qTPd0&5H4&;p195WYC@$j`{F7csHg+WeC-k^n+Hn6F5{W5d+J1?fgS$&T*RM(uB6{Ej~iJ1x1}7J$SHN<p@D*g#2pgZ8dwTucL}4"
    b"5emo?U>_F_JdzieAR|<F-H|~%h=w#bNV=`zz{$&99~?}uY_#GMZCG32J9prt_Z}%O+D4Y3izXl`Afrm`+7>@yCk9u@Gf@+2;n=#_"
    b"kg*RPwrAK0<JS<YgKld%m;LN@B8L-tU6~#G@US;rcgx9%i-K{w2t*Yv7;Gl*>PC2Qcs60~X$Ks+8q^9uFP#IKG|!#j1y)L~1l~Z~"
    b"m+@!chz66v2gPK6^N5<%`sN?r=#>c>MZ=wrrn5G`+@Z@k*hO|*JZH~vAkC3a@LXg)<qSg6D<{BA!eP=|wp9K1pRx+t;*&Z@%9O=("
    b"gJ)lRKK4f!)>EspdL8SUd#ejN&n^m^1Alr31QGm&>^{)s$Jfn9w`hfgwGcg99amxH*2nKVxc?Z_W{_n|*i>#d?g>_H7<}jT8XQr1"
    b"y)E<nwD2MPdEezrsec})%D_i}k)8}F@&npNgIgaw0S?rla%?GT02^nnzO6=|`2mi(^u~bYLeM$S*68iQ@k<IWcYyEhiIpwS;ypMX"
    b"@q^!Xmoe)3^2jSSaC3gO5%M<cDzMZWZ9~0*m6fNzk%`~KVcnmU(x(<azT~6aB}9iawhx`%*7YavgXC9Vg(mjtmV|WQZ39_Wskck="
    b"Bh6k=r^>8mXNhX}sPa90fx8nC6DLRr*z#_87jHdxvi{@>A~*ax+)E5f6vl=k&2rO#<^Tik<-7*+-Lz%tuBFy(iyc^SkP|Hr!n-@3"
    b"Ts`kPVJn;CVvTO$ee>Qe-{(&q!o5*_dD6W|NSenH9!iNd^ou<15t<<doF=9%rGg#NVhj=yEvbV-_~fQn=LUVg=<FCRvrWXH*E_dk"
    b"J3e(k^@}9kmBYlyB^<4rfGENQFF9FMT#|E@WnEYy4guAQVEpHfnyqggtj$_+!i9~&B~4K>{8I}SyFUH5Q}4wFU)q1}in+emd}7d&"
    b"R<Sk<W&$ep(^+a1Pm527tv`m$iraEanfDI<u%;_`9wubOoQ5kJ1+N$(co}bc2aboAg>k1=91CA*Gn2{qI;(P=hC+Jwa{u(YDv55u"
    b"&W43g{ADVii6_dy=riK3o{sm0>>c6W%7_^C#b`2tFY|v~hjPP@zKGu%QvzNK>1ehAdsYj^$xhpbuBs{`jRDDg(<81mID}t^pskg="
    b"V{c?*6SF^tYd4<QO8Au-?0v}hvo2R}=EXH7xV}GV_9hF>gG1a|e;R_(ShEK%u%RKzAbW#k+j6kE+m~|(TYaVGg!{iUjQ{PC&j%~9"
    b"lDz~6<24ai=_liZ8?PN1{)T>T!sZ}u#qj~cnp5@@B-D-;g??)vN{hT%ed|<fubw;M`<+b*z7;Ef#4S(HnS2IcuMloK9Uw~Qb6i~z"
    b"_j`TQ#I1Rs-XG4R6?v(iCefIB6hCwRAIHCp=f%={`p)JYJF{aqEjl2l?&nJ@-#>L}xSGG>I<f8k>%~`K<&4I%pu&bqn=~;J)E*SG"
    b"Pj2cDKPip6TTr>M!8ufYwO#7k@XqXT@yC6=pA=gRKuSF@e7&Ow-+@1le(^zD@b-6yo7BgY@-6E$S7eosZ+Dr&+zsRI-y1x+MYTQg"
    b"r-*o%yJz3T!9U)!e%*$rd$RG5{%6%y{L#=Gz2Uac$cwJd_6D!J2Jj{GABV*HV8Ng7d%MkxZtd&xh`wrYu9fCtoI4=@`p*0Drn)Ax"
    b"t+N;ReAy8loNw!2H*~r(doXAeT)_Q<zW*_Yjg)GlG<(@9mp>0M_3;$L_}@3}$%BIG@wGEF%0407gMA;&xaHvOcy4jg56jO_H_tvA"
    b"K0{QWi66!rE7^!>NTDG%>eNj(;;F7XzqNC)t+U`j@%Cu{m*IxuJKk~LRiU>I^!L6S-dC*Bv~d05_kX!)VpF8#Sc+bn`(c(aPMu2d"
    b"*pBxWyUqH+wie%s_=cXEUlqH`s@^@n@vWh)T^+wQ_s4t#;r+!M-nw>dmvD&Sb@+}K7fWCl%Wr@0SIW=3BaJWC#d09S_Mi7vhlzQV"
    b"8UAIS%k1ypSm#?eEMD#)g0)>i4{!V=cK;V0e>882Z6657i?6<YWVq^|A6(I2+3x#mkV+S~@4xOde|%&p`q%G#T6t6|Wpa+5>}Us="
    b"_Ps|wahgZ_3+ls9#QENWW4QN^D*LUib#XD`3Sl<RM}3Ct_%UwN;f$#mUz@70W$LNl4L1J!z3&BMSF844S#)pr<_8P#!1u^jrrwk9"
    b"&@dl$85qU+h%aP{70s@{1-!iMGlC(L{KfQ%|NX)4#y<3~u}bs7<JuOg<18Gy{O{{u?8OmgUghQqzuo$~@Am)vAzCZ^ljqWd<?#a3"
    b"XJEcM7$Fe9Z_n%j@8*Hvx$ySk7o#5xc3g=6_-AF2<=goX;ZQGrNa@#Y?>*VI*VP-H|4X(x%eQ#nBRMR{45J*8cLY;S-ynY1?1~k1"
    b"1+(zewdI$5r>1_{_DT3p@prTj1`mDuhi&{$Kb%K(+OaIru!_7Xv)b!lBf8enwB48NkIv65oj!fW)YqMV$d=#4KQV)!_w*F^$0AP$"
    b"e{%ILqx_KXlxw)RDZFL4qxJgMwgGQZ@qwkO?4kfo3Qwq_%EEnc?$`B~kFME&-hTI*tX&O+8}yyp6pXs?ZRU#0UD4n>(LhJxH@nuX"
    b"e&e9`)aBT@-spxM``cRXSoOCbb(pV(*wVD9XgF!<1d6xl3887QrtY_GyLvBJPs)j5^PxRuE`G=yAe`;&;75ZITzH`8Wc-cUKJT?u"
    b"{WfN^GcfIyzm(V>tL*-ltVxx+!A`da>=LlL-L@4w3S7Pm54RD+0J!3{;i2@WPgdQ!>C$8H3UZgNc4!Z!bpBTR74v{&O7{V$Bq($0"
    b"ckUGOrhO2xd$xAgJhif8r759#5le~TY}=o#A$;|8yzcpM>1$gq&Ix92jXb?>+Wfbxv=EVs?X)RWZWe?}IgeYOrF?;F9AS27JZ@ZI"
    b"kGgWtm;XNR$vev3S$beC^%5+APeV<<IR4q1-`Ch#RP#BGSNewkVQp-4xsg41@deLciZ+x)C!4r#Fw&m&dD*w)m3!2`K`Sc%=|$RL"
    b">MypOtIL}3#tz?~PQ_7O{|hkq$-$aFoWB2LMfHy-yyqSKIX?1}=ecXWlK-EyeYV+Y@Nen03}GJs9o4`4c^!W_d_+HvqA+mAVD<4|"
    b";K7%!d2@$@r_z@en{2Z<%wLEHa978)y?wr^=j_q8zIe^MvsCZ@?7M8-3-Q#$-a0(qm~z+)v7qt8pA7rHG#?^ry+8H-pQ`L%St&M@"
    b"dp-N}fnba6_2NZmHsa2H<;q-FdCig5M_->2EmT`)#m=>C|51@Nb*cX$*e4qQZ`n!l@I+%A3{6!WDAuH(%3o7rLs3C+3+qxeZO{JD"
    b"XQ{@jw%#(lq+;XMG~Kgfg0^_t3r$;@>9)XXV~hGpTF%C{my33}^L0iDz={wfNK*c3PIgboOZS{m)^un?e6%UTM;2{mo<v7u1Etb9"
    b"bv0VbEYe+*ly?_b;(gxjxh>wyv5iK@AHAmse6M)5eZ{VKi^a%5p3KCNna=t`xN|4>*yGCTl6JV&QHl=dxQ$k#7w0f%5s02v_QkTT"
    b"@3hUUeRuIuSFAXA{8Mi~ZtDvFllcxl<_#>Yo@v)#W;PERlOA5q9~SX})aIGLNcp^{c1OvdVRPPGrai^~Wf6Lx&nb;EhIsg1HqSP%"
    b"{CBgpZ|@7@kA^S!_C?=o`pXpU`=JvHdgtMzJ0iULE7Ww^Z-4j&TYD<LjtXb~CgrwEFoEDb9sfPz#K+KM_JjPB_L*!XU9+)y%vK`c"
    b"w7kk4klA<kVsW2`uuAP$>~*wnlD1{%F<$=&EgCY$6+3K^>5>0Hvt~N&Q|s!>QHOdmzI^#L*~vxIF>v-toSPOeC1wsMNr9{lC%rEH"
    b"qbpZC$^T}whip0EnAo0AHbL7DQ*iAa=Q+;b<KGKgl)XCzsZiadVPx_Sevjbcip23O;jIqYr;~?lL-4u}e-9VCE*_jF^7T<M;?s*+"
    b"EV{jZTy885#ivAEIxeZOD?361eEYuNGgTFkzVl_GiYs;x{}@!k9gCflSEkjb!bP+k6-w>1v#X+BFTZj7Cw=4;xL;ALh*nyDr%u$p"
    b"l_~qSY<OeYOG3bIC{UFH=|$u8U1;&nK^WpA;xYCt8)b)OGviq5E2->x^f-#Jn(y!lGSa*aTOz}3mrcJ@KZo}5D||~^7{kfM+YVON"
    b"W0%g?dP|Lop^J7#cd<+0kox}CNN+9UW-dVH`0EQzzF*`o@sE9e)u#QZ)*<5P@VG0XTgH|A61}!Of=<k8%xfCx&x$)*+BUS-e(G!&"
    b"YrPd$8ULdn@l~1rEB<acZ<{nOnsII1LH6^Kp`6d`{<N1~L+jA%Hu&+ec}>2-a`$<3ITW}>%T-N&!T(!5*BI!oD%knasvqIQVWDxF"
    b"QM~ibamL&e>9#CwiRR0W!m+Y<TW4JS(?6VFynO4x+1bCW-0XNJa_HsSW%;kN`1xIrdas<%i?#ju#eG|t`M8yD**?&9yL`>)|G0kL"
    b";=)U?CUXI=&o5onx1K-p%V_7(eXmb!{I6S;?}S2KAMSp;>f`;t%&&Lar+>FDJB4Y0RXsnqM_Q+kn<3xv`pg!O-S}e8KB;Bx>kAKD"
    b"V(m?3vlc%X_<2u2nE+rX#xt*L0w{sRr4E9O32Za#Uk^Meyq>JJs>*U9Sb1=JiI(Ic7U~Qgn8aP!QjYDEph$mJvQf97L|tReDg+=^"
    b"a#%K?7kJh3^E)}6BdRFy+DdwBB`HLulr1yNEzy8|q~`%L7!D+f%g}9imLl3`f$=wRpMgSysT_Qi2DzeL^=o7m42{o2+%lrYOV$;w"
    b"i<o?TNOOY9xhH2W(uAdu2jdaJ6C{vS)XMP{8=7SB==QbM;Lz+S;tfE)1{uvdW7R8{@;VR8WU>-<$!K0;NV3VoxlpyqjcEAzgyenQ"
    b"gl7MFj(TG~7G5DZ=u$C$iYEy=leo`tYkwp&6)Zfvs4--DlXy}pF~C{>Xq3j}W<TQiT>^NJhkUq@+SQgTRRu<|yVF4jRONS<E=*pq"
    b"YQz?&OEq$%PVs>CkKQJx@$(?1XD@lVv&g1GwPvI78VCX^<oP***9_>{Dll?c!%9BYIFwCBU6{Z_#C|+&;Uz;e+*$M^Yh-2R4A%q6"
    b"D_%vh?zv#*mgN~0)W67TA#Dw#5JE`@PC=5&>Wl{jcYcXeR$v9SrpX$z4MGJnloTDfHF*m(dg-Xrl&M0v3(^Q4VivOQxiq|lJQV8)"
    b"ol(V&<3sedgiHjQbWLan1ey>*W^5Pet@cut;KdheQJU9FodAVo87w?-vsHPCpfY0eL=v~79Ar}cjXV+DwQTZkG>IqC!b{^tgIg0>"
    b")EreQUNmt##l{KVx`5rPtqBa-AEA$iS<<p?2|OeT?pZUyY70&0OUx|Jeas09rip!^t24C>CLqvgv5CA*11}H$yFuZ|hXW{*Khw5o"
    b"A1&We<#F0PsuhZ*WK+XL5=K(b$(d6F^6bZ6t+C6TKiF;WWTLCIjR4CH-3gvhh)%+W@Zpu);5(`<yX4qfpt<-A4cxN&`vA9-;uTsM"
    b"cd~@E<!fb@4e@rK^A{=X3dT(XuUN&3tw14SA_zR{?*AEC|8|?(0Y=0DOxgu{c0nzKz)T{kGIr%zwIX?goNv{iS)x>=RIIIl5*<XR"
    b"q85q+)eewyZPQ_PM|S=JUq}6k{(Z9_(QLCMPPtqYqOSK<7k3=XHDK9A*MS|M?8DKfzBhwCN3Q9x2~hpIG}!02^CdLXO(AR|_%NA?"
    b"t8qH)z%=6d>^Gx7#=Sm$UY}+l(-CsG-W?bY&WmP{{l6Gr=Zbd>M?_pwFu1$71vcr*RVAyE;E8R~Le^(AYdQ^PlZ>?&AmC8QDfOpP"
    b"A_<!wdarRoMKaLv7`u%INY9BNohhO`Wf!DGVCIv{KJy21-l}~3>?HfDrs(*Zm+xIS8xQS+jE=+8Vcy#U<a=v$9Kq&Y(`R2?jo2Nh"
    b"(Lvla4;#Tap`&@9(Y)9`+*gT1c(?;!-orOX-+i%8_n+mOw5UFDCu?Ws0RIs8X#2gB9(pYG?6wdqEv1Z8MKkBN+xQR%7h!fgxb+lH"
    b"_S6bGQkfq?#xcqycENozUw5YGljFMI!|@l~Xd*M-0dsPj?jOWeJq4Z3QzH4#F`GV}alO9tBlg5x!enb2V7YnQefWA?`8}w)>T#88"
    b"GPk-M+oD~~aXGra8c^Hd{@vw%51>*-mYAs?P4LyXLxy{`JV}MZ2T~c-?duLk&a>KF797tvzzNgahx;pa4mH<)#+I_fSHuJNMHg3I"
    b"oD-dV*c&<%C8ujkA?ozZlHJVI+UjOsT@N0N6d%O3zDtD+lfTRNC5}|Ns^_jHrtWfx1nsPUsi<?e<_)TBg{}CC=fKjU=`K%ge993a"
    b"zquQ#+*{V8*&a|+2wmo{RM1MYVnj5mFcU81Kli{Kd8W*{;&Z#S33D_!eBU^x?iV8Awf2x3Qp(ucnPsP6oi5pw*Ih^Ls^*#Lf+9l`"
    b"HL18k*>N^>zp~8boD_K`9?bN5V1@hEb8fl9BchHcVBds`yU^jyEAM4Hw-KIL7hVWyO*OjjK%@PFWPhp2m!1b~o+8G#8Lj*=_vQw@"
    b"=zOZrm@oyW#D?Yu(=KGfiYI+{Zo1zNt^TdO($1V~z@7|6TlFk*@Zhv>GCZp@>sC#;lJc@<KXl}z-7f~FD|eU^jc41UkyS0Gf0Z#0"
    b"4^JE(-hTWJ?CW?I(zfo{7<|NqBZh5QgRSQn(TC%$gFQ4Nl*3zOK6bUHqdoS|T{U~={b#Ip)&giO1#^S(th3NB4xZN^^UuR^elXgh"
    b"g>~2G!@vgP1Ln7T<2grqzSQ8m$Ht36dQ*HohKZcm{=SfMJ?8^_fLfR3^PZ0xS-*$#8koFM>L^4QYx*phha=Zq(VF|i7=JpfvO%+j"
    b"ja~OXB@bNG!S{fxo<_@TB;QvTEs1GdO58Pd_yB&R3lD@}$ADUh@CJj8l;$}GF)kqz#}|3FWm~l7`S9W%G_1}j4i=+f-S^(5?_MHm"
    b"!CuB4E;r4#o=8xI%`u(g^){TxZ}dlk;rSRQ-{W$W>qgFDTTwh39C&`G1il!49mjE<ui%}OVMr@34*nq;b?HmGF6${fY9Y}3+>kl1"
    b"KOR<L_I29p+=V-@n&KA(@BaQ;F;-LIYBtyGwY9|bU@)ZF30_LazniW;U*Weu9fp)(v2)@OyxTB!_C+;4PPlXLZWC|piG~fB*GE|B"
    b"a81WG({#OaEf~(}Qe2@>h3jooMN`^xv_+T-qHqj#(5l2P{GXqa1qlYj*u;GoGjXil7ANfc(2?Om{I@~hYN84P+8v~qL9yXx+NPpj"
    b"ah0Ib@t4h&u&u2tV?IvXWq|J*`vJxU=DhgEPcOsl;6p2LW98s?j{B}fCYwLiAbi9;yuEWcxEkhl1F8s{XX+vkME(O09pd{5p3pG<"
    b"Qu*1HJ4Lu}pKo(WWAN`$FOIjF8{@r~ddc`|I;dx}@|w@oY-T;dJ38p=dv?&L!p3V>d<KsPYj8z4D&n6t2T;TEl}{APQ9>xo-{yla"
    b"Y0rFqQF;$YeI_B<%ZrH=4u2d!h4J?8c#1Y|2hlpi1F<%|Eap?uA+qDF&%BKLgZM1QQ_LTHXiRJ1n&(DQBpcLwew3bnM1MwFVh~9Z"
    b"U;{)u<$$d-0uTgRQ4$?aE$bvo=yjr=42k&wznet^L(v}KYhef2qL2yp4GlA!^UCWoh`hgdQ_Hffrm}(v%*Liji<Z|#fywiA(EhY+"
    b"1V`Phsrw;(h*q?V`e@oDEp%d{FxfkUUN{deudHm*TbBGn^Kf_PwQhfZt&-nJ^jyA%hI^w*E1FFrH1FYADE3gz$4?Ywma5CYP~23c"
    b"?{xUVS3wj!749U80N!Iiy)v^(@(WSH-2TVSGxYU@B;<;8iL+-~!ETNK!P8g~kX4{mhFy{s5uo|qexm5m+xHo}xCZhgT`-6gUQ%Lw"
    b"OxS*A=f`n2Z>nOWDdCGNXhyAU1zFMB1HA5_RlyTAqcxhzluiSqDPE%Psh@mugC_WoH}wpcL_S_AMyIZMbI|ZOj(O>&#f!V_L`#vg"
    b"$PaXsh8S3l0t(6a=+_m2s5N%Bo!T6!f~CnY0wOC5YxHJ2W{vt{Uo^wt(Jgy2Pk5=mzgo4f<*6KJ>>x7`qWW2(Ktm^1k3<k!W=Eo_"
    b"I<-&0FQaaV&SJseW#6bzttl{qkW;8DG}w0KXh;z|8X0Wi`O#U(s`|UALVCmRSJN4At_7P~ch8lDi^avdUuOzcw-#X2b6m%%NmHE8"
    b"u^-YvUSeLcA<ab&qaH%*R$InZBxOCl_evB*W{}<H*IW%kk#2+U$tCB<H|4gptg*#cQ=`IvXqevaI>63}#6E+051K42sUlS3(%yg#"
    b"8^{2sF4JMdpA!Ke?pq2$v4OJDq47mTM}5+P>XANJ-Rhq`{43Df9c$XRz2c{H;ke9NfV`<6Vg#0xTy>OygBV+2$gGyW!J4c?5v+w#"
    b"o>25fR{>qxWFpP&8SHCw+jf-e+T*}h&eo`T;sI`In<mL>u0{+TD}3J`f@prV0&bbH>HP`YB4HQVrtA5h+<`WLO@rjqe9k~kW>a4k"
    b"tz2GK_5IplU63$Wm^3f?u&y4#9O9$phR65pmk@z3A}3tB-`7s<qRI$uenZSRTb7RIJE>i=`FPe4AIdS?LXAiwcrIvn)&_Bh=8D41"
    b"d6BJgbsp}h51$C1^5M_%;9p^LZ#*8yrh9xH?!-~bv+8_N%VMwt>zN#|p$1-e=QWW7A+-|g#a1<)8j*Ct7AUgi+x1IeYlnqonbJ10"
    b"t07Y%N_dqpof48E5N$4Dfv5y;ma}M`qm+-n9(XlVw@*4x@OTL6suhnbEC9PsX;5)!<i{^yGVs-@9&+9YKf5Z>bPh&!(+ZZr&5@vC"
    b"xyWwl4qkK+KEa?KBsq%qK&8&BPZ_Hb9cbZ95EanLH(a&jYayGQgGr@iP<Lu9y@C8bOwgctCdkDwehx^U6~sE+aPgf62WV3ok(usx"
    b"_(D)#Kb?ldfUXgOn+a?!Xm0SQ)0p8bf|sFb9L&_nCsxC98t+f$;8!8Ft<vFC)j(evH_$NcK-si<=e;ITQ7b`RG{eG!7Bx*@N33@n"
    b"jaHtia<xby8eHnj^kz}x1muQgFdsN|0hzDP88FT1|Fr>y>zY~|;Jp*P3wdcnE(0Ig7-gFQMj^+Sz&a;wBRVI~!SMP^5%+YmA@ds)"
    b"7gM4uk;(iEUV#ny7vwopc>Qr9w{CuR3Hx%^@#@wrW-bi)ZSs0p3PZ3|D=~=rG)F-E#jJ50F|<`0TKtm5S$59n$S#!9!VbbDa)$E#"
    b"3MdHF#|4j`vyeqQe-vsaBr%sA=&N?zx_m9fC$MU{p|6}d*RDRXKpDrW1drH-wc2AaouSczATXs4<X<i{OcS^eVQzB~r_xJ4^hZWm"
    b"_LCA_q{&kAV%7J`cW;I`VO4L|sscABZ7E)0#XJk@Oa^L0a};U_*M1L>T)Gyi>bQ1-hg`Zem(X88XokAayFt05gcjM@xXT<&ZACu{"
    b"k3Y8ys&*+r@Wf?*m^n8Q(MEpMzBEU&@Fq#=(@TTM9~f_>GB&iaR-QxgM4e$>O@>kg3<t~(Fx9?pxUF2QYlij%iZ$P*+Ec{5iG#Ls"
    b"4xx;f1W9aUn8W0(q?f*d6nCnT0SM^}U=HHVV*z5#n<7Y2$bJFXeGpF_Y&r14%ju|@*TahX7@aT0BZs4QrNRTjb1Q^JWb+c-8d^iX"
    b"EhvaVsEUKRDdfx%?&^+nP#vA+egXRT$b-Abx14_A>YdJA>;oZ1ox|NBfHrduycP8yCKSl2S#u`2ITrm60x3T2C8g>(aMQ=7peiyx"
    b"qE{BWbq^~mP*yZ6?*$m&C`XO8XKL%85i5vXCWm_^M|~^byOaF7x|Z%QXw*3b`7eONc4(SF*yDXL-G<s12xJmWz^zGcC_={uUn|u7"
    b"<ES{zNj+8%>33XUW&)irC0_R&g6CIODk)?Ee@8R&@;gm8>n-VC2|s{`U_lBwlfqo`wg-r@?4}_JwPl5%b9D@jC?I(74Q^?`@^6X2"
    b"L*cDN$5bRqV9SuE<&iCfh8>4f)7iBV_?U1T2TRNT+fy{Cc4u^L(id=yvg;Y?RB7W*)<Zaoq(~u}XjcNOb8A4<gxmF%Fnu-r6%FyP"
    b"Y7WI!7m7fH=I5`;>SM3ZB5di*S-ZX1ip1x04Y%Dn>FDROl-|@$Xh^=>tw_%TDvx_zVp9}He0*2jhl9AjlNM_dn=p<RyT4s)Cqyq|"
    b"2-Xc7@t~`zt1BKfRf#=#7r5;cCcSZ+0O|S&p3L)gn&)-P(`BPhw1)}bodPAO+MW!N{@fC1mb_;YE;hpF36o6gxeE&IJB3rC0J^>f"
    b"*>o9XMVd`?NQsrK^vRL<c$=nM^3%#q$$c}L#IxLyWV-{UWU>ABCXbL3mxN=zyO#R}uiszSNgmS*^eRhLjL~!nE8C8GSr`X(<b^z)"
    b"qaoA0VYv~>?}FdXZ+pe=nyGt4+S19pj)tDu;2n9og?A$@jE$6!q~gei)j6y)`4>WPid8XW50T7%)_@rm>D<~Grvn)TPpKmGaW^zb"
    b"(%17mZX`yy>6aZFHZj&Z=$v8|?@Nr2CTPzPY~1{u)9#3$^|~cDPc<b;DoSKxS_Qu#Vs)!aM9mQ;QXm{~#wOT%>>pvII@Aq3E=y>f"
    b">7H6CT>^GyfP8<ZKpo0lLJ_lD+L(>jWhZz%d5Ms<&p`wm(S(bF$%wd-z=i<*l3hvDos;ZM;AI$!N7dYj#MrH+F1F~yDx^d-eIIMY"
    b"fyKI)HwYmDYkW2M9O)cYF=4!J<COZtL?d1o5d2Om<mXCb6NF@&-BLz@2I$Bhh1L!@3rMAjj$@NtYB@MeXlWePCYt)R)cBUIXA_!i"
    b"A<X|;-d_PeKlwbQ6xL2{(w*#iaux`)_tOAf^@jRN;9a`Clp}Kcbgl@FC;bmtPF=zxrhf%bM)UAn!~e}1r?lJghu)M!I2N_(DuEg="
    b"C0)+a2nE;+ITSK<4^VfqtdGX^YhS@rAcgQBNz)Wah0;4Uw3^5~x;+UPg|D!5rfj;V96}M*1Ci;4ka>QzQN~y1ixkuZop%$wxsHj5"
    b";6<tv;}b@5UuXdjNuq7i&;n4RdXy*_0fYv_IQ}&5?Wi0{wm6A>{c!~;z8=mfCU_5cC#lQlltfmiCdLQYsuYQFYofsg#=)a<R;XDa"
    b"oDRH5xM}`VZAO-PM~d+e8Cq$3F{tb2lu7r9)_$ZjH_Np<qE)NZ>uf`|4t$e;ew5`;L&khbt7t#XsWX*QZ8@V-9Vy-M_n(fTBbrB1"
    b"V361lwwsPm*_|c61;&I4+V1w9h{&|E+I513H}2M(WX7RBjcAQ<b~z8TZk`L3wnn^ce?0iS7CPTp7clQERaVycXlU_}d^5Z*PXx5P"
    b"J~V7F`4iphmeQ+<*aY7oj*3|9QP8Hry)m=@XoKDn|1dc4_;t{&Mh-AvaJWzuTzp4OTr^YrFs=;62muEmH10#L*gg5C^PREx@zmiV"
    b"+~0MjtD~<24_q;4Yl*fvdECuD&v{ZKTJ*f&Re0lxJQIJ3HQw2a@!t9;-mHva{Ux+9nr#LL`p>@7F-)XW?-iexXxnoaYxjNwe=@|E"
    b"moN22mf;$VKM}#6k_x&_5xhE__YFsVR&}`^nxWB#@do^khJvxoIL7_vOEo=Ff*0@568TJbveU4+vG<Kc9?5{Kvj>|dG5YdR3r}_6"
    b"$c<hzxMQ@l2@t$#@gR<v2Rp(9&m6|p_5>a@{T;o;3Eo=11z<{}Lin)5E{o^_i|{UR#Y>2`@|nv(<`4FpI2bWMt@&9j7>o{g>`J%R"
    b"?@p%DhD-_RY{X|kppdqczYb!<X10zNJtHH$DgA9UJ-dg)ha#rgQ63ArhK9qx<Aao5F5P55SU{1!dYXK}@)K^hzX+B+T)R6K7W>R_"
    b"$BVJxs?UZG9Zv8+?k0FCPPn*+*R2aO+s((ftl)RM2g3zjCh9mE3;I5bi^tObS3FJye?Ct`Mpa0!x#{`MFF15E8W#Jp={h<XEQn(B"
    b"0at<_*#7?0gDNno3ysiDyW4OXHyfYI247o3<~tCKb;JgPYa<x{F4MvrH~wbp$2;A=vqU&5nlskx`ujH;DCqt}Y)Qs@L9?L0-}mFI"
    b"m~6g<N9&p<qUmvLw9itfJa{p;73}F=kbE^Jhj1(&?$cZ*t!`?50aG*<wg20=S58gSxYa|c`Ei>D(NGdE7KJ-~W)PeFFpl~RA3ls>"
    b"+i^X$fwPO$D79+3WXHASwP%9!lO<l5q7U(e67ChXU95)AG6_6OV9HjwqK1-^j_Y%U5G{<M(2`~u7<;FSaS_w7T_^1`6EQfK?uy;Y"
    b"_jj19nj+K6<2YW(=m|WB!_{vT0}h)kjZE*v_yaEDu%&5W=d<jVRwXC>Nt3ihjMZBj=hOI)of{70xGMA)_nc}o4<jp?v>DOswG5Rk"
    b"{m6FsFL3AWBY4PC1e8(v=8szbA8sAgSMdFZ3pO3EW-n|4yW<V3^9RVRn&^>(bRHA6QUkt<<D9V2uILWzR^7H6X{ACWr+rjC)g|h1"
    b"WBaPen=Bb55pJWoqICT-5+8~{HA~j9P~cp~d|3$%VmDAc8Jw2XXO)C(x9~Kj)KBo}-XtGm8h?L!L|ErThTBdwF>8Osh+8ngg_DW9"
    b"v~I|l96)6KrfA7k<&;$GP!jt*kqtyYpygX>rkoW)t??drxeoUSovDJK#xUscfc3$ZM*4&#-mb*0K6OB4jn`>87Ik@@#?em35e9D2"
    b"tQTArj9nh+*JgTV^9SJJfM*j;j`Qg%JU|Nq*!Uut;GsGP1GLqa=C=D~kkF#%U~0%FS*(Z%beZ1!k~IvqxQU|b0UhqjZn~ScXwQlg"
    b"u4SWa!_CTWw%bM&{X92ZrE{6c&?p4*x5xC9-5@(1ippE|0`*=_(PRP5mnAn@+d@CgcT;!j!=-W|OWUbPSv%dt^s=0|cFxTw(qDPn"
    b"g`FJojm=y!d)B$o5^$<r)vR0oQ~~aVDw_8Jb6_DYc1f1f5w$5mbm#mMkye8tcy+Y!F@m4aRdghjR#8t^2;DVWy0ASDc0x5Lk0YxS"
    b"fV1xD*7j_iuS(Q`>n&s`o;$z9O_lIl4Teeq@~%fMuc1Xm%gO@u3EOJXiCv%tWlF6I4%xfT&i7jT`1pL9J<jm0g%f5IlO}NYS__W}"
    b"(1bwxZDie6Th#Nh-|nV88NC5odeV+G2G|mdfR4VcB$ZTsg4I-4Y=E5EMKs2r;t@@MQzcL53;qze1t%C3T}GD(UIgwUcrwA;$$(Fz"
    b"`^3zzQ#{tWdicGGZokF|4%^yIgy$>D-Bzv3#deL!u{wriq@uw#CsF6<IO<v=!1ifB+l+Prvdt+0w@)LC6YXR#xl=1xU7nEc&ZPkr"
    b"LLRJLL-CSoZjPqinyp#I(NiTF4`JuKk>PjPBeQ(f>%rPfC}OoXABPARVc4h=CHk4`7qiF?>V%aofprLJmP*WN9Kog4*Qi#@rV@ir"
    b"6$l>iHn=xn%Y(aZsGGXaiwUaCkrPUXU@fpP!A6%638+r4Ab1|ovW&Z}Xcb+)3PjUJPDIUP&x~JWNS+OlNMLlads;X<GSSXNwG?!K"
    b"16sO{gEGdGG!f)#WHa1^mq=E?hOEn0s>>QH$U@EI`&ow~Tbyw{lAM`&FbU#Fs{*#(L3W>|10V#iF%HXcQbFIFY73s_G+$&XJ(_Z+"
    b"M$I3iGZD1mP3b9d(exy@lUwhk)n4hfI;&A<KG}K8p~=%kof4O>=Fxy1y{ymWkr0`$$<n@QPK9RwsdWUe(C?qMrbMXb?bLiqOD|qZ"
    b"MvAIo5}k=4Q9M0iiW)Mt?-ModZM0M)Wn{D*B_aOIW*RU=8J2F#yhs*;SneK0mBuk9StE76Tmg0l)GYn51X(G(HXl;$5K7)>kSTB}"
    b"K!b`DHw_tK9crpoa*QRLT?cY0d6ztkb7`s@m{TaEsT0UEot%$XX&E-!g?&EJ_N>qwNTl-H?Hc8fvuKD4*kw93pe_73XaJb3R@;dJ"
    b"DM;#c-S0$utC#<@g{Zv*ugbmBO3GU42AQV7vMM?Q3A{Rbz{{*U;r4B!9(8(sm2~6{Ht>RG2QOh5Dq|SXEXzed70ISDkk15Ks=y{{"
    b"tK1;86v~8}Q9T*oOpdHJ<32r7nj)}^*5cu;Ag#uFV;0gx#!;+Eb|>hw)OzOel<W%DYH+#4y7;oW+|-(nAbJC3Wo=Wfm#C=9h@vz`"
    b"sU!P}s9#(KDIJvN^t*}l_-6LA^gL=w^IIiGu+<k`8ZogWEdpWtqsD6D`EKhxSpC0<=(dbXXiQ()j7pho4X)694Xa;9LM944c-{0f"
    b"ga<)%ra=94T+;MSlm?+o%gH*Q4$wvxtF(<K2@AS_Drvba=jgRmq7|#aOJiz8ET>%aYdW-=xW!`<&M;JJRiathFvim(jQ}t=W|jE&"
    b"wt;SB-rr0&XArB>OF4o2n&(IuDV<X|7O#11CcmEe?Q2CiEIig?3(C##Zj6s|rBOCErZ9;mv)C#d(83HEmd9$n+5#$iH9-i7E}KTL"
    b"*;Ff*DvK_e3a)P)wgSDDYpzRaHQF(q1rcl)!M4UzOB6$C1?=<MH5Uv%MWY~XUfAxjZPJ0K&MTGGXc17KksS$D?)$T-`4Q^uIb8oz"
    b"r{UK_s4~kC<Oa6T2XL*>)_Lr8JHk~f;9;Ms6`<HPqJ{<2y<Fh|mZlA8Zg<l~))!Hj9uxALk-qP$sI4XIvEfKht$YDc8MsP}B6%Mo"
    b"j1aozC;idd<w&er4y$~oo{sP}eNiL$&a0bxAlP6KJgF&y!p3Z-sTI@~)N$Z~ShjX10X!0?jEdhw7_R@GTaSsF4{S<7<1FE24pOU@"
    b"Gkjj0$c?UV>YNR-&+G1O%|RmUDm5?yL?z-Gb`J!up|GP{Eb}YeJ?Nzfu?UIMnr|#4dfQ=9n`m(ErgBuSE#PviX^5Jm7^si11>{sw"
    b"hoVx`9^tZ?@tU7#x>_To=fiT&d(T$QtJ}Hn;FroF5M9d%tg^}wkTzSJW(a8qLu{9}(!XOTN0be_LKyirB%XdKohSAI4?b4=w$m}u"
    b"U@Mf8CdHP|mX;Xz@Y*RogZqwd^Q`WV^uWYw|0*L-Jl>@}enr?Rz<{9%p<zM}sCy>txS-_7zQ$Fw%oDl-J_poGMVSOIu+!!?^Wj@1"
    b"y2_vM8q%(nn!nglr+*HvJmsGZ=N$ug)J3`#Z6&v{rPRhoWqG)&dzx0H!seZ{EoVmccqtC?IP@QhW-?;68!8s0XZ^O{XsKiO6|b4Q"
    b"OI7@P2wpFUd9x4ri+68Ldplx-T9w<_)&Okh1F#KrI~9<dcA`2Bl~kjuC3-vxIj7{z38Lmk72lkUUfpc880-mCx>M7pZ`d=fQ}1C2"
    b"UX4F^b`im2!0^i(+RnST*KJW)f`<rRc1e@2qps?@>P1HUR>;YdGqX4EbfXr2GAi9{G}D+Esa0D#YmMo+TaPe4Pu>sxE_smyRrQzp"
    b"S5<Fr>sVhX9OO&j9h;x%UpXZg$XVS~-8F3(J5WhIO#SdKkt2AvDX1d#!rPkvo`|QNshfqa+n*!{e355UwcnYZeU{h63)3GH9&w&)"
    b"MV0k@US{2$ZaXJze*Ypj(Y^O<<Hm^7gU;7$?=?h4qKUMmOo0l4sK}43tsrK9oh|FSa23u2FR#^gA`J*0DmM6P!B*Ic^axwz)AMp#"
    b"3LUtkEv4J73wP(##fgG(R9kCAL6SE#q}&2EAaESmXltdWdvmYm_Cq%a@)~+aZFPL*{F1z;JJ5=Zqgkq`pL0WDOYCS{sclf#h@o<c"
    b"*VTIM86q(x`5q_-IHiE?RwyO9OZ3XUd68}XpiC;{OKC1NOYk}uDQ>~<QVCv3c3?-txkXx_h0Xc6lpBnc=o1Zld7Ytag~TqJRH(vp"
    b"gN7C)cxy^^QSWPXqNv}~-0cZg``xPjUSfIOU7xQ_XIRN8<zMv9@B~X7k7YyzS9Z^{1TX6%*md|>XXC_)q0qiapH6mPeYt2xiJgd3"
    b"k>NXiMD7;yWoPd%zhIM#mXSHz#^=9q7X#_jr8OL}Q)CpGq=6Vk7t155I=aY_Q(H6mUiZYh>e?8v29Ypq4_A_=<r2;*vV5&QyULUP"
    b"z(X_Y^ITmkp4T`0Ds7Q{`jhT^ov^8NQ-eD%Q=imHIO>^;d2)p1FQ&7l@M8SK#?7qUcYy)_)OxK{w3nnAGX#*H6_yQGyJc@#^A3q8"
    b"cuTA88>-Un<JJTBgo`lxO=X3JZg#=vn%{<6@*-7?IJY1Uq36ven_q+n1)BhyPz%^?TC=idWit`k%Z6pU%ha0UkiOj0rP5w@U^440"
    b"$wIWq^rAvHO!|!P<U<vly9&g){}M-?+V&b7jDrK|&r^SPD~LAM!gF%4d=nh49EPJsL}@KttNIlpa>`~dx6D<7XZL#+fTIo8@)}`!"
    b"5h)p}LbU77F#JX&dbE(;2x19aF{4^A&?H6eL$Ql2YtCCPQ#=oKOfWK$!d}!&ECPRnf1%X;Q27R6D+nF{QBIITn}V--754H>qG*y7"
    b"g^Jnx;DXl%`B8gOfD7Um6oR+9OmuI6>yTNM&?)SU-^MvWjPseoW=^6)w3G!j$BMgo95SLdj=FAG%`fGZ<?&4iUOMo|y*B-kB8)Xn"
    b"w##ZapLPPwq?Vw7ou+zCBnmR0AuQv_Xo+g3ICH6f#r7@_(DW=7LN*qvooUs1s7G5CD!DY3;I#*JgW}mFs*~Gb8N))J0)m=!&hZk}"
    b"Wi6{aP%y26#yuOpVWLghsIYes9>N@EC-!RTC?v@ZhyN9Gur8C0E}x>%a=12mnT?1c4~#nt+_RSbo5yV>Hb$C3?60SGM*<um)wk1="
    b"4{WpcH{%4+r%D$tbNfPkM!7><u+tbIFHU>(<i;8dyPznBn^(oR2am>2n@i%``u_y5awY_E5S!Q+U3H`S-Hx&TxLqrLzc8ar<Q>fo"
    b"TIT>!Z6;dPRB%-E;U*eB7YVxRldfK39SFE9%6~C{!{+E6$%Z{+HJ)o}f4VL;vdEz|Jgy8tl#PI!uZ$AySyhPU8Hb?N)1t^C2tlc&"
    b"Ze){Kz0Slt`pGNzj2WJO!Cs@gZ5h8#>uW5U`xJAH9S(+cK=}FAclNN@WV^vDzD>u5vEh*N-$*zy^H}pnIl$hr{@cf7HcC$ADY34x"
    b"$o|y)i_B26<xi~kt5r(@^_-K?;Sq(-enTnj8(UoQ9AQL;4PKV_qJ0fd<#Ld$^_uyo8!BpR;>QYILT`@XJ$3`)`q=8EFUEyh$p!}3"
    b"iS`-ye0$P}rkj2BMz^Du<Whr_|J2B{&u)zGvoUy{k1w%Az1G)cwh+stZ?Be`Xka56_{IQ|cyDTY-AMBZeiQ_;V;fQgcB%YtQKY`W"
    b"bwc1+_g*bg(T?C1-YAimtRCe$p`yr`Dw$s?8ai@WtjT;og1R@R9fNhOWN4*Y5-)J0Am)PPw#-yUYD|Lb=G9pF$c2?eHvx6gn+l3@"
    b"MuGOp2wwcg9Flmqe>{Kd$TRN^Ys@zmPixoVES$h44g*D77lYp%EeUy}zF-m$eF#sCJS@6l0{F%(pQyc8<}O6C$vb*bpgFFuNfrVV"
    b"&*?YTWWi`1)FmSi<2Nn??iz#Vgy+HSM=m!j_aOI2MLXR|C%*6ejd$wFqM*otV<TfWZh9F7c~GUh*C1bZZDauP{SHk}E=KTYe~$-w"
    b"`lZnlo;SxUf~rR(R&md$Keh<?7;sGTlm&ltqqrfA;5qb>Q^6ZIE@73ir5xcG^W6@~wv-oUm@6kj%1D(~^M+;Tg#{z4bJjn)?%d6a"
    b"R}#Fc`Gt8h)A#a^JM}orjnEg0->?J=NAX-|SC9NQipPyL`B(#9@OX2|m{qm-J0%Zm9J3>dH>M<8WYmrn%eB!lkB-m&)k?VCK4%H^"
    b"@3~;6mVlPVBsU)o-k5_iipN)~qw6kwtrBH&83-Oz25gC0l)y{!57a+;D0v-5j&jQI$oQf#a=EH67+ZH2*sFQAU4V{8qRT@}o}EdO"
    b"A3Jbkdo^hP`l(<eqj<>@%*m4ud;rkLAu^}WIL$AdXPZZOWN_CODfvz`iWeUx7t4F(^3FD3QB!t#e`4Hh95^?iYcewOzI{EkONd+h"
    b"D-dJ4(GS*jNw#2ut%~|%sJGvnq%~h+4HT4!7;(;038^@!i^@s%=b|IJkw_pd@Z2EM1#rMxvXi>y)DvhNM_PpLB9n}&q3nsQDOK3r"
    b"h!9IeGMqk!`V=wmhADPC821*sfXCn;kCC468Sn=T3oqS@Gie{$#oWRqo@Sk7&j|PPCVvLN&G}-T1_Uj<JU&D_Q_uoQp2G<OunGuU"
    b"cr>LlEGNFm0839^o(CA}LZHvAm7;+Hkz#ZKp0GD{yZw1{=~JiWK#z_P6u|a&i)zVtcGE?)#G{p3M}}n=)g)d*5}0Cy%Q*d9t37J-"
    b"`tx7}4_b;WZH?j~qn!?ve&^X;ko+Qbp3|E3j4K)Ok$B8vob&7vy}2Fy>8s=qjnpI_GMyGS#p8`hl*!Pbp~mV29!luDblGrn8t7^w"
    b"4^BLcj)2z`3T<mTD-3IVn{ZcG+>7HBuiON#f#T6xd8j^0=S#1(Gc7!iX5W^m0z*y|-eIaKns{`dTW?L5gJpiB)Spi<T&@BAxA{HM"
    b"6Bgc!x=SQ@A|D^Yi$u3|Ydfs@y0H04)gZ2Eqw~ehOZ2G~_CQ&oq3w@ss!AiApYE@3O4Fr7NRUhmZ<+2Czej$t6^-H*`kfkeWT{?p"
    b"x)9V9t;I?4`ZPE^l~_>sMj>=&XhkILqLoES4p<p1A$w6p_akKJZlHMVT@;VfUxXYIqd~B=EP#dii8|XT@)>v@C<Jlh6{LmQ%ng|1"
    b"6oDox@kmSL2dWHNXv4ovB@`|aq9S-6isu2YtJK0n3B10Y6wl2@@9Bs1#e@C2_Rit|kFfWFi{iZZg@4b?Ff+)qGl-3guIwOI>^W&%"
    b"G}SdCJE%wPIVRfE`*}~=rgi;OP4DsO8rx*8$UZAn$Snz^&ABBB5z_XY^nLGnZ%xwM*c%fDFhXun=%4q-oEjO#s%?x6V#6ZK&iy^J"
    b"yRh2iyna40sO*>L&+q^9`}2e*2%K<);l&16b3uh=-7D>u`Y?6y@c#I&G@dv$jaSaD+`$V}!1@!QyzndBZx{7jImaY5hm`@7UTqD#"
    b"dIzucyuqTF3gdge%Q?SZDpf#gzj(E%_(f;G?g}CqT=D4_PP$?jTbBJ<j!SHSvg&j!LtMW@&n0#<ICyAKDb9V2F*DbxAE-n>8bT2{"
    b"g(nh}m3(|d<;o)JIsZT|x$WRVrZPB%7g*6k2hxnJbf0u0x_}Z$&KNQ5b;rTOb6-c$*sWPvRHvSPOkObFlfp|noJ~@AOH|pxV=MO6"
    b"`kiLE2C~a^PoCdp;gQ<mcz9p%I%p^dlOji^?Xl|AYmY)T8P=<5E#_O7u{V~|j9RPQDtP)Fyd1{sC06vzUK92PMZx6(*V`F9kt)q;"
    b"JZG?kvz*}CpJkMak-@9b!PAw-lj4M`(a!ELXVm1LcAc4*yFG)q&HycqSJs&+si@)7$_HIOZ$^WM;F_Pw3Jb|rSYeP3qtMS)S$Ta)"
    b"Z6lCQI^7mNb$%M8T39(oL*})KyiGS}G*i0yKH_<Lb#5K~e|rrNkjqsr$-hyY#sfqC3p^>F!SmG{)fo-0i)nr%s-b^OVts80;oGp&"
    b"#kcINT=yZJR*hlZdFw`gNw*<aOfGG0R*HH>Mmy_LEQJSJk1<ZjxwVD7n}6(TD}j)aH)x~{gYQryjRz!+=QH^<UQJF~pQ}Nt^A28>"
    b"1tC+HF8Sn8ZKupV-gD|4M@;#3s{~l1J6KJrz7-1SB9MzN088Q)(3-f$3ePn;E`o<?C|yW^&UeGY7@7<s{I-&K`-JTV75NQ4ZYvi|"
    b"xSG&(syj&yC=awEdN1O&GF_r6Ht^3Pp3bq)G8%@zKbpc@OCi^ijNEacmOE5LrE*tKzvcCWz>ceZp}Bkgp<_S|;q|Z3CGgHrBk}dE"
    b"+Z05+-*KfM%Bo_CI-^SUKh?(>o}Z)bui($fs|U?04xxWup5JYpgL#@<S<Td1JE(+b>kB$~=UIsXtV;mrw2GG%L)1NN8qwc3nV=u)"
    b"4yNP*^jFJp-Me!YNS(`#zOzPUfGoFZA(0KOndpmkUGw36yno<4D~p1v1mq`Ja<MB&+4^$)+*jL7_$n-gwK0ZQvh-)@-d7Bp9&!5^"
    b";+Y)i|J3#p9!u_8C@|5;`6<II@FIN*i^x_B)VP*IYVaUMy#WN|cbhto#%n2I@=Bo=8Y!0m{okh-Rh>0ZbZ@cWfn&1~PY9P8@X}JY"
    b"K4D$~K#8WCa9<p9NOUQhTvZKF2ktG1_b}eeTB;#ljzSM~cq&@K++C13ZJr&9y>rqv@(1>+A{`YXDB1RGq1w8n=c}wpiwm2ukLja>"
    b"KTkr=(Ox3!?rkhaQB^?~Q?A6~$dk?C?=2y{yt$hMjL6yKy8bwsv^CDpCc%6L@ifM7_jtaMa!W&C#6cB2XjkPNy^!)qP$Tlyu$WR}"
    b"aV1YSf37aCx>quGAg{}Puo3P3sZ@he7c9V|C}DVF;DTe!&(g`s7HF;lf#D^fYDpNbBT;iTP{!_;Bd=V~733PpHg<4(&b9ZEIuvus"
    b"Xj2?%7D^>Z;Z=*vwid{FL%3Wi+Q11V*Fq;D|7a`6a*<uY>$AM~FXk4mviR*!?;jBUS2ZeasZzRPHl8665$v}DP^ofi-cbZVy!)z-"
    b"acmYf5*ifQKa&Mwu0@kD)`FbEWP(cvH;Nd%5B{M50j-cFmvB+`rbLF2&1^iF`&2LF)}Aq-%tuSe)8E|+WD9x-1KMD()ZiG(=TRPb"
    b"x`J%#iw@PC2nOP<*T`sa82K~+hgkN5Gb)FfV=TfA^rk^%)R#q1b6b%mP^*de9^V843qO!{r}sjQ<1Mm&8i4n~3t^FG$+!N1l{Cu@"
    b"Z!aEu&Xe&J9-%jNqT=}#;eJ^MT7b`1Rt8j+;jxy8C|_#O$}g=5Gdw0=HpE32D0x0hn+$0?RnS)q<R1;94^*Mz(&;cNIMkP3$#cTd"
    b"m#Xlsu7HLgv=eBLGyPE+9Hh=9DUMI+OZWY%>^}51<wIWG<MgaeXF);<q3x`V8{(-(vkFQOt(d4$q3OhWxYFfhuyB>W)|dr?n$jQA"
    b"^8Ql+P(F@)k4`@3)ibVLMM~MCWKQXGP}%Hvg_Y4o4bKw%ppVT0V6zD;l@r|uje_Pho?AH`;8u=>a_G%);|5-W<?(REc8cp`Lf%;)"
    b";_)qq5YHKIyp4Gryj2{WFr<ea{rLmC9hNzdn8?2?lsb=izi2dVh49lRuaK-^B$P)y=lpn?wXRTB_OiS5Fg!P)>SlWha^3G6{14Ll"
    b"Qsi8SC%7)OHbc06s8NPcR${g<gNIJUFIX8woEb$C_Li;43E0TaBzR>g5n`7uI(WI30ODrR4bAd_wX(}!9L^rGK-&!+>17F*!duO<"
    b"`k|VgpVKSXH8W-=K~^|;WK`%p_Avi6zqR%AOI!SYpPIG4AYE@b>pSX<lvR9q>6*@ra%(nl8sCR!5(PL7bsXtRt*@%nu%4d%m8VgT"
    b"x`GoY<ihr?!BJSK8LW2ChC0WeSwbB=pTi)7xX4^PE(1T=i@s$r>BO!^<7qsqlWN%V^urr?*TJejA@y9JN+T~x!f6BaX*@+@jgRd("
    b">ksAF9=%ynjZ<eFeN@Hid?VTN!}DujllKnwo%zOe<fDMO+Ufo3zj5%Gst}^_%uD^;tcLgQxPvFH<JRWYNp5mp_j9^AY&@KmWs8=@"
    b"BIkZJ{||&YD)`7C+y0|kIt!kk3Fm?9vDpruf8IkAvF0R+`&DtX(HgpcI;O(aNytZthx$!Zg*mJSWCRI%E~{AsuR%OxDAqQSB=H#K"
    b"@*@hz@(3j;UO#+tV;7m@_b7$5(XY*nx{#Nez~(Clsm2wMTMRFVaz&gD`;E1-1c<a*=uYE3{`T-G6cvKMp890|i`jA7paGBL`Vf!z"
    b"na?_SxI_LzCbTo@4NMo<#KpDDn9FHTc7;wBR>ACftB`*px!Jh~Q3{XgI!S^iwJ|)~!Q0rFxdwZpIulfoEU60@VCMWpJQ^yW{TOG#"
    b"A%mCWE;B2|0kzzy;o$YRK`V1QD$$J~r{d}GSM|-BX-+Z~hDUR1;iy*0E9)%SWALuj81_uT1}^62Rvm9eGkhrP(EANCr+F&Dr6OU$"
    b"ogH-gXxx`5l2Z;fj)v#$3_g``Ee5_(-keHdbW#r)Ih@$an*J_<Al|POhcY&WI?CoTp#b#<|0&okr1laulw%Zkl5@i1+~UrjriR&z"
    b"<sg-}We48k3{S^f(fA(k99A4uhPIT0$JQ6{y*QFdm$pGU#x{`is;^!Yw+}bP+RFNfQ;Rhdc(Z_iRcE)%Mt?ucQjaUx`1t(vE-R!&"
    b"{|ug6WDCeaMuTG^U*qu8`}&~lo$OIjJ`<$nx*lZHp#y@Kr43fFwuej8qqhV6RAzmA67o29GC9{xPPr0Z+E}d}?mKkm!R&Nz{Jbw$"
    b"XP)6wzl6RJesS;NQPw~q^IcIpA*RWX;o$~E!^ahu*~9%EwaZ894U#pagpprC3Xj!DdIkKVVkP3`P2(N06VpdMD}`4aG>l`)B~N)#"
    b"QGY$nKamxu#m`q4g_ygcWx936-^9P<p2!e%^^`q*G`Tlo_y@NSX#cUo&M>I`#ug)AU!ThNLF<6|%;!Mgh#yA%Azfg2rh<4!qw(pH"
    b"JJFOV$2$vf3~zN490~r`w`v$R_a9$wxS2LzovMWxP5|i{(x0%{5C9!6;B^x!)f`lf$#_VUChB7zU%Rb7y|dKA<gCus;?FAWKMvY&"
    b"=FT<Yku`7mQ+SzQNG|<hJ!$}9Z$~aX9p0GBn&JDVNB2!+dgG&s%GKhshs4+EP9urhwW?ys6|V{2fhRQr!{e_#69+HuiI3;rnV8?v"
    b"HjNjaUC-!WlLm)6FCx9`{HU@0<Lse<Cb$V0c*`RFJdNFtc%sLtCz?jF&y8e^9Uf-ao4}uu2C86Us<SZ+g~#ot_(=9MAIt~Ez!P^h"
    b"<{yjwlD!9d(3-dHvzcAmBkyJK1elF}5@$(fr(Bd^6B&z?j{3uV79NF_E@Gfa%5U&V@V}8y3PJi2{zK99w<y2P;N`*WHrzn@>9V1i"
    b"@`s}=XY$BN7<@08{gUyJ8#?h&4jtVP<1e6LbAXabM!M5n#9hb;tRi@z4GE}gqc!ALK03amHdHcUz>z!PSkF6#_Ydv&*!%@Ft0Ja{"
    b"eS>@2CgJ)rA^8e<UK^WFA8j7h9=z^F{l1WNciMN9YcLa*&0S2Cl-j}t{Nh5$%R;51SIlVf@eG6RmFGoRHt)*~S3<p)12CF+AY{$G"
    b"dg+d#al=5mO(5=Y>6-%HGkFB0HO3u!w<Ggb@+1Cf#Is6kT^sbifdGso;?ekzq-;Ec4ZvGRfsf6_g;wAfNq(Kv*=^=j&ZY3&Y!ubQ"
    b"D6sf7-hG?@DF~a7C*-JgG=JtN^RW|bZ||X8ji~uinvb8-ID-p=FDcQ?NWeZbEx0ZP$LwU%&mHkx*>vwtfTz8#=q*kfv+b!46l>Dt"
    b"=&E=T@Hs5f6<4E_ZZlw3gx9&92`OG!9kj37<M!0+w133D-d30zH*(dsxHX<*Ut}|<h{qL8q6uc3(V=iwEAU2KMQnzvX%>U~l84$i"
    b"_1sY;>gU#Y`L8@>Kr?yfGv)j4fmWI2ny1d^Bs09xWIPC2MQ;2%|DAV|5*u84ZwS8PyH2ubtWe}tKDX#J6xT_D=3cR>e`4%6!@Lb%"
    b"r7K#`O1v&2)oI@Jd><g@KiIaq5}gU&aF6(<j)TutYsnd#Vs3k>%8eBbxHlVf>-ck(AehWa$)8zH8ztw$-kE3CtuwFMe*ek@ANNdW"
    b"j5@A0uex}3&50AHr%tlnaKAI3^}!jEwhdAz2B!b~@eCd+f@Q!wDzqwUO~bKL=BkTSH$PiAczkEVCH1=@^-MW~#~%qvf#R719~+pd"
    b"DVzX~Rb9ZNGk26{{S^H;b^XpWUUR}!T+r>m6A$8kS7iS5<2dQadME!Q6+~tXX5G0o+PDGz)!qECcPI{$8~o))<PN;Xu*;mO^yLR<"
    b")(6|AI=9Z6{>|XQXrs88cZt&E@TgEw|E^gqo<fQ7QI?V5OBlPR-}U&BEW8U+jE}YBP0t8*8rEfDd%(Lg>Kk^e!|z&8Q<hGjpM}?V"
    b"&CJibo-DjmEY;`Rz|%YNq@4?a=iAoina2Iql9L{tg_jqH=2<g%;{)06+N==(c(Y`>S+QQ0b}c5<RxeGM#;t0fMfHf1g(rPS%z7Lr"
    b"qgi+b=Scv0jmyTHT`h|t^y^<!hrjiTv1^mxuUCPZla-fU?bw0SZ^bk82TT9Gj*pq#UMWk(&cDt{mgW`wB_`TG0^B+Q>p)#|$7}c@"
    b"<CF2=2DnOwg{?|fsif4)?SN6icOnF_{$vHG9zY3t2VMXcZ2e?B{$;j4u(I%MN#<_564CQ;U?_H@@*!^SFt?b?ra#yVlK#nf<RD`Y"
    b"9<pr!x);o*x3;(PEThMF16785_nmkgEvBEc-#3{zyX;Q9IS@Kxmmyw@ZRU4UX_z;;Y<fXsYz=%0UOwW<Zklb-(BrdqMK11X<(pcL"
    b"G)vDNgJB49+4O?@34A&pZ@L_EF*4I~%%FRD?Y2_Hdox^K7<|w5Zsnc~J*Ofa(yj2P;VC?X-n+@jC7uZ+n88{)b_pVN-CgHa6}Gi-"
    b"Rho}F>*JCBnXr+Lz^CEOX9pX1))lm^{mzW3x4Y}CIINGKSx9|SdkgT|8x&G_KI0K*8qufXDJMhdMzM8mvwKqYmx;H#n@~!J4xRRc"
    b"B3gZrSMoqgzVPX{XMRwhX4ed!VLE5(Z4YVPtjadY{K5(cudcRF_9ec$vbWsYFVP2k4|Rt$PkyTVs1rZqok7y^)TrnbUPU@#!xsWF"
    b"#2(h->}OS`2%3i_25JDy4-tuOUe!pDou5kM<=&0QXYicT3*RBskTHhGs?bxz4AFFmctbkt*7oQ|az5Z{`D>8#Q)wM=I2(`4T3>2d"
    b"wJ(ykTuc^wamI8dM9N3J3M#?^UhglIiObjzgi$bm)$Fdz#)B+8DW)U5&kJN0!!x9K)E;1BKOt;_YmcCN5h>t18}C8oXOvNK0mB&{"
    b"Pt9Mtn#P-zeSWOW6@10O?^c{)C-~a{TVGsYuM1@+iL2z8<qm;>AYwicl{ZbtjN*qJyeONDl{r73{T};Ew5s_fj9geN-_tt7GX#Zt"
    b"-Al@1EwiUu!sjBasS=c*O+BhPcv7c>x6Q7YS)VWYg)|;$3<bD3$mI_IqNDBIa%~awq&FM-i!>L~`hzz;4xSQo@Pb{HGkCLZu5s`P"
    b"S~ZOPAm0cF*+C{jkUhpjtJ-(9a&Dg*I1Ypr)8w=0fm!TKiVmjmR3nT2WZTJL2r@iY<qo-M%BS#h+@!$_p8n<quzj*rtQJsJ52w}_"
    b"T;RxiC)F)p?A<qmrwsR})|alj2mH<l(s=txt>ruIeP6YGoTR7)wF6a=G@fJpCQ^8^=jj<dVkl|6bWKY2EWac6EfAF2+R3GTo+3+n"
    b"LFC)&LOVR<l!G_YecB03rSN9K3|=+y%+H)(N_KDcy$Kn-`rLR4_2feC{9|P=)W=r4$+`Sg7RCjKLNa)+EW8wv<N4*7sp8Qk(MZs7"
    b"(OfJKsEm!&_VCBbir%9|SHuSAK4|*wG=sM&Yri_5#uF~2GB!eI95q5=HY-@g^@-piP$u_4h}`4Q3(4dFeiB~qs`P%DdmK$v8s9Qf"
    b"<Oj?7kX&5B%0r7x{^h_K*g^dK=d(k`89X5iua9Kzmr2pdgdS|?o$G}sq|n1A>z>AYblym~xt)riUy~iP`$RlGy*?o2do2GiU^z|W"
    b"J@+z1h*6=7^&TVFc*G5*O$T5>DrgsSvZ*q7by@fE{`b;&?H~I=Ozi1g>l|Mk_})(HA%=J%+OKq$@Xao5C;A&X>GCrt(SYHR_$*f7"
    b"DQED$9IIjv&_LJkLK`q=1P?A9!9WYD=yHH0qJ89QNl)0StcpKDbA(ihIEy<1PaHhlub;`6g@obpRn9XHl^ii^*QX}HSs>~lcm!`j"
    b"B4k+OC4crpWoP|RV-D!;P|I;IJ%rLrL8@IFpQQ<)*CF12LKBYsJzu5D6!GqJ@S?8NGmODny$T?>iV|Vt_HfBqBf~RXh^OgGIN>Gs"
    b"HpvqXxcICv;t8L#wr=IuSCcM=ry-uB^F<CacylP8vk)t)3-|S`1W|*MT5<+(zpB=|`tl_n@q9YfbK<fo2*R!JTU#{__q&$pKZCb|"
    b"#Hr?mjXG7*5scj$iy98~8Rdqt6NIow+lL|}2X`UMa8En)oR5H@p*&DoWb=!Nr>PYT4-IXkKZyzdL7G}#l9kaT18{vVhBpi@Kd0HO"
    b"R}T19>b~G|JbPwulrTJ83$AaWnpz*grYND_kdt^u(g7tn5mHRx`@dKJ%5lShzH&u=9pG3#e!Eu6rW&6Ieu6B_#r1(ebb|EqpHAmg"
    b"koCNdKNio=t3iI$)Pw2Va{jGL<>t68mGm8W&2NxoaS&Fr97HF;D|-nv1GkEBB!#z$(X(m@734I-Yd}0!GZFHqO-iJ_<KTayf7zar"
    b"zDN0G%k9&pqnspz2hZ=x#y{r%7*qo!2^s{4--L2Te^oH28u6-Rz0^iLFRD&0wLCn&d`kQ)-QFt;ejk^*%e!^{B~Btxki%a0nF<$F"
    b"@Jdd~9HZyij=t2uSs!qWUc3fhV>rv3WN$5AN=~#Vi%%DSZS-XmH5spw++(_yBk+H0vYXn&v%$gRzU1I(MUu6Z1FeS4LHS(B&hL?-"
    b"+9;&A%SzShnqTTQ_gvn+Y50|pFBlTTHGxi3%K^E)FscE2Ti%QGOx82`EI9H&7ji1ePm6GU)F$Mp$y=t94#xp8W1TBt#oWsgw43$("
    b"&g8cI<g&^z;<?(T8Vxs{LpMomhFjdl<b4T~2aUTB&!@veXe0b_i&H_F%;4<>SOIT*!4uhJ0(tWEh1L1};Yz=Z=eI<$|CWd>ud58T"
    b"1R$OpxE4IWbs!{2D5%T5x{pXN-gu}v{e;T;vmkM=$p4LT{=1t(93M0GmiN!*z<@s^|0*NBA=U_u@*wAsxI_~u#M$~}q?c=}^*KO%"
    b"Y>wS*a7E8WQzp5?&HwbadzR}e^ApWoMNyTP>GFKm68A&H?*YQI_Atu`THRBi%whLy;K%H@m<IE)w}oY*uOmGRlfTX&UAxNNMcaEo"
    b"*l2F-^l^Mc3)%-;^}><33(XpZqWse#em}Y7Bs8Kt4OK(@G-w6jtPc;S!ya_3ubiWf@#6{KSLAC`fnRsV1A7W$y{O;r7x_QLxufiH"
    b"kg$}QIMco|DZu+>Pqe`a4w=TsN(j#*F-OyQGILcn=Ax+F(-cQjh;Ov^u=KE}fROsjNoW9FgdBo8)J#1Bbz9+eEW?zw$u;ygfVG4M"
    b"2UEO;!ozv(SeJ*od{3i6Dh2*oYxnbhL3;}2Ro>+q&Y2mPlgd|iUY>Z1B`7(m#;UHNyjoWa2c6#2j;G?N?4XO7o=_ttm7&V}VfPQi"
    b"6(Prd9(k({Kl`M`^hf4Zm^gTj^TDzALg1P@Gj%KA_~~(2<BDAtLbV)!-__GDe#ehA>DCt<ySe{#9Yf&R0XoCCfJ@<}TY%9h>+eUL"
    b"?HZHzppi=b4w&E;>K23K9tXr*Ca3Cn_~CxK0r%L)XOhje6u+gOFLb>C7+z5-deBX0GOt76I$O6}7u{?W#g1k8GyaAdE<@dxOcxit"
    b"l?rYyT)WnJw%eLY7ylB_zeUp!4GS-u=W1pZM&w9CuKc>k^&bhasX9c0(lcs48<%bjSt=}6J?SU85=i5vUo6$X)e}hV;603ZGf}M~"
    b"Dv4F~KVAR0Sq!@D3FX?sX2-s=X(Ylr<9vgVnH2k=G3{S!E;Qx%f`MRK7Nma-0T-yMHD&bN!SIAaq9-s9@&zDKIK;AHQ9gSzd5CM#"
    b"+Cur9DY!;FC}_V6?`;DTRn#iNL;40E-xU&zRh2sHgJ=gMi+gzQOei5px2Eqm6w-W%$D0n`$ap4z@OBT4uWR;%RTCawceP!Uj;Oh8"
    b"zi0?O5H(~_>uyZficm-*V^euO9P@(*!3k}nceOr}x*~~nKi2A7F9EFI#W&|~S6zrlQS;8*&yJaXh7EM3spkQPcXUpwMF&J#j}%A`"
    b"YtH=2L09#8R|vKOasAD8cd^{L+Qm8mpxK}lI(Tg<LKWqQH4;ZW=2`aOy*^^2DYrnnt2dWWMJJyLn*s~_SKV-Fh$q8S0(((Y7Q{JR"
    b"Q>A?=S7uh=Pjxii@je7r=jLP^5~#?V%tA{#c&j@KuBhP_OWAqMpuPWc0+>C74yn@09%kWl><v_hqq5Exy_GfIk<!_Vg#JPqzGHoH"
    b"L9ah(7hds4P_0NYGbX?6cku8M^2Tk}B)2S>c_g4g1DyM1T{Jv77Lb^AS2rqC(53D1LNk!?gL}`TX07}$Cqk%yS;#$am2E6UhjDT`"
    b"ppMSLR;TX(O+DvIlm`D2&x};4!Lb7A%9&jUB~Uz6%NJN?_v(1t01{p94Ld_H_{G+&k{ZZ=_il2bg3)9q?=5N?P^DpG*K!5ie&(+#"
    b"sIFEe%N)MkpLr!GHV`Yj=AyXbZafeS#Yno8E+`NSKzLUHvXLUc`S5cGe)9dX=NiY6Pt0_B{T+CC!u|^K33z&9e@~YTAA@xET^q{R"
    b"vG`Sxl|q!f<q*N^BOhK-qD-jAQNZ|8liFhmJXN#iZt??Ry<4vd`?_-1e%z;Yc5Ofd+V9V2KO6<ht`tiS&b(+UR&?gGgzorDJaC1="
    b"BM%tp<_z@Z(uc_QZd1+4VIw*z=XXAQYJBEJQwh(I8t^B#-gUhe>#u6@jZ!CgM8k5Ej@YK^6R08)FE0cEhq`Wz&%9^`zm)x)d%(QA"
    b"5t@THB=933N~Kdbie96hRVN{b+4b{6{w1kig>TNhXfFMA7M|NOJ^?S^Y8H%rcz-M29Gib|>ZcGAav1sffmAwSFR^l_@rXT^T}XCd"
    b"=q@~TkRsl_s_J4r_*XnJQOhTgpN!9<+s1nDr+dCCS)C}e;_a}qi2MbfNB1w+WS1VK>WUTcVRx4YwRH|FAVi8ON;SY2=u92b-YmSK"
    b"n0<F+I+WW7TD#O(C-ptx*B2j*H9qfhksMa?VW2DQ2zTB$tsVp;tGNd;si#u8t0A8O1uib|m6*q`m3N+59_s_i)s=(1L_$z{+`;3f"
    b"o8;+&J`?QKNd!*(Me*AS6xm!Pj5<pzPi!<}*FkDHBUB=a#x3$J$8`pi?zj`2M1GslqSHlFem;<$fHhs{#RC_%c$F^l8&^$wFYL}G"
    b"brme{?Vd#}<$}ESyc$65!v?jV`N&;a$@YZ17Eb0+anoP4OBpuqwYWdT?R!EWN2`8OF1SDwEFr>-D9H>(qsi4tHWkT=CaQ*Q;~G?p"
    b"Q7dIqT@=ySxEoJwe`s%!>ECqDUo6%f4VTC+`Yq}fEN585u%Y;fSrY*c1!)5-KWGFt>;cMAl5!+&!1BBCT=Z}EdP4rqC~Sqq^I;Nq"
    b"(O$}49l;=Ag5-6v(eK>ml)c9HrJAyopjyd|T}Bak7yVft_<plzdvhPdi$5QZF+74~fwF_Npv~`b$*eUw^EZn%W{h!qEx0wb)4ioh"
    b"i3YwnY{zXDQ|utgk+>2sCr!;B($ahG0D?4Hq53|GH;pDV@xvP9v^Z_M6hWDnD+c1t?Q#d4D`81MUQ#bRt!<?sV<^61q4C9dGibW#"
    b">?7=%(?{o06M}ZqUtD6;LBUXOiq?{}GA)~KMP(*#Lje#T*@tpN8k<X<H+7A-?8_`zgLuWn7+s8Huz@zJL?s{lacdRyS$#)leN6_7"
    b"S5M9Dw-bm5mLE!!;(Ec|*5%~E)Y|p-U|g6`^$@W25ik}KSW_Eoz@zsR++(de_RymBG`<jTL6-}@mOm|lQG|_q&z`}}e3?bXck!+M"
    b"$B?*6bhMmZuhr3Ao@N+lT;wmH!8+pLF~$~+z-3CwlbWW>ZN+v;mZm*F-#)2BSQVh~C~LyTcv?H{^hDF><^Yf%As>=Jkr5QgJGC_R"
    b"T)y5|od8<fgzE$E$|0Kd>|_M(K$y@1Na1;$WJrMx15rbCb2abFqXP0P>8`A$f2^fiFPrPJK`;9lVo3${w#0_5Fqx2_(M;|8fNv}~"
    b"Nj+Va0WYxeC#)Y)=m1LPT>?)>8*7lkB-ppX+pC4@1@x|wn0Mh1T;(h4Kk7@4rzFgvJ=x|slg7`H!4I7>JVUpkldc!UL#$}eEcT1U"
    b"st0{EA%-oas{34(y`B&Vq&pFlPccI;Sd2U|HzC7n)Mxu=7$J%x0)-D6L}1hkk~u-yxVwA8(Aj`a?%4IZLu9c46(=LIH^dsrBWWgB"
    b"bIW|t?`?>lb6jv9Ra5zk{mwy-Ti`*@ho=^F)(VPA>x;o7l)gg=D+(kPbQP3c27es!cKdf-MpCb>V0Z)$4Y>jdM^DrzQmv1T8jz+;"
    b"6&AW0nAqrSyI;A)^$_ZD?>zfV&HXxwt$G^Bt58{C<lb_jKl%jlft?-fxtQ{?or!1?;Y_!5t~w*90~?dp0&M}K1i$Ojp}IhLrEjjO"
    b"!~S>5Z-rLHVz3!JCR?TQ?@$WxUrD0k`oRV;^jP=kvYI1?qq+Fo!1bn{LD0=u3Glg-gvB>oNS$YA2bDSIxrJ0~GDfTcU=7zQW#yO("
    b"2KOR<;N9jeY<-7f+RII~2<NjW5<xTlwiva2Kcq&{G4~<~G?V|Hik#X&D1?^vg8wind1(piP0$sYKdM52FW^AvJk~<dCkgBPi<|H="
    b"25C^Rp6g(i2e;q|6<*tF7$xWYE=d#O!#U7qv~yo-fXH%_1df3=W-$S$gUqo3K>PxhZz(=tu+HOW_}d4f&eK)$fNf7)?VMtv{bcdJ"
    b"FqEA8j#D{nvZiwFTn!TS2A!PTKw{e+JPNXh4ME&kOw7L#M9oCJ16^?B1-oOg=f#Il9Y|cnzhTDjflBEKlM59MF|~idEbvn3JgRw!"
    b"aSn=FP|tqLA2ldySLOI&6zHs#>3T2XNhXA>xfg>||Jgn{9QPmkxaD_b2QvvgKGN1XX5Lrz>j`Bje!U19J>A14GRL}0FwJ^BGQ}!2"
    b"iCFwD{;#y<m$0#wlo-SmVRZ0RaB|pQz9$~8jvm!OcpP^SIYd4h(hT^T!7H6{%W)M~#$4j_z`{~!dhgPi%~K^EXDWFY9FR*}4>aNG"
    b"L|8R=z#bW6B4udrn)ASNLV^DuJdC4A^7~9-zF|3UlO&hAHXsuliaDyP`Z`CslS?FKprP>!4R}eDslkTIqVW-XaKs+}<^G{aM|=Qy"
    b"7A%<}v=r?GIcT_oMi_~Z_oK|7v%BSEFcpLMqzaEw4enTlc>cdCuSL8vB&u&!&e_;z|LWXxt!A*Zx~$WJqKDad9!bv~jIn|{Z}5za"
    b"${3vtKbf;bJL8J`8P_;tMGLwLE*+AV!Im|&#JmwI72q8Mq-{|<`fRJq`0Fz@>!u9IV>Ql|NOlv(B7>WdLB9+ZxMaeU<^OC@?)G-N"
    b"<1G!f9|r|t(n5GG!WAY<eysM_3L=S7ABy=AdEZXK?t1eHG~?V+v~7xsC4SwIdRa_i{VoXem9F_?(9e8~?{24$`2;pC6vgb->qYo2"
    b"iuW<?CBK&kH+hNrScaFpVHhSRR|e+~fa@yy32yQV*+;>s2K8vwdhqa3nIA4jyaMZMCL~?=vyO>SkUQef&-1{BRu=ui-x|nI>JKBF"
    b"^|GMD#2;4%)G%>vspdd=#{=&<@7FB`p{n3IXh;W-oUIG{gM30tvT?TTdh`1kUO>M}Knh(zIZJ->Aad-;P08(%f`9Y{;9+ts|2n#`"
    b"bprh3b>vE=6^XP$aFq;jhmZ8p5T{8X+D-!>LU{KVdtH-=S4djXVqxJ6Ejrj?Cx=CsN9wrdTLJ^5jd^gsT>^Zek9AQ%`VA!nxg<~!"
    b"bv44(Gf)rfM~ynMr~%ykrUMKQ^eA{qQe!Piv}NedCoe&`fwbxK8_=jJ?zUKktmGs;eisF&8x&!d&%X+f8$vGq5)Abi%}#s|tV$Oi"
    b"9CC|QO|EOK6{q|s6fEz>Axzcaz!n!d0fpUTEP<4V!jn!|A|m>Km=L@|4G+17#@gwv3TPf7z7W-0d{x3J^JnV05AimThCj0)gGJGl"
    b"e0}Sd1~LHipS#S86(pL6Y>K?*S7E>scsLgdRyD}ZK;7~Zna|mQAK6^#5?ICEX_fU@E@Hmo>$tut18F#a%y^I%A-}bp!|$vX4I$26"
    b"3-CwRp%GbzcqD{yodAb^F)!3DJVwyAs}$U#CW4M;@qzYH5O`^%!=9X=9tc(0TbI(30g$@cJN55M46X(Oj-Qjb=EaLS&UJ?6vhzbf"
    b"jqE+`d33Mw80#jujh<QISi!l}<45as{sI)t<Iiqt0du&+KexUUZ|PrGGdJ!#8d}nFDyS;6aM2H0Gjz0HUMk%SxHa8kcwcFla4Oun"
    b"TsD4Hz2g5m6ZBWU)It<AFw1&ky}&O<S6dD~)eeJ(5=(bx2vwqR=Q-5a>Py?buqvOGT_fJZG;hK{65?dO&JWU+k`Guaw9Ze(efD*="
    b"tcSV9D_D3e7;A^6hRi$bBP=S;W<OT|75_!^!f{q`MnLZLx9k}^q3sCe&<b=eq`r;6NA~!i(ZaS<o;R=iuJrI9QK&q}N~Zb~bH0GM"
    b"YL$TcmAw_VgDwSNR74h#kAE9AF&fkpT8kSc%?|AkKk7m}5FTO{P$XJlCss!jb9=g_saEj!g;)|x0>l(y$+~owuBk>d5vfrWQTnu!"
    b"mBubSQ)6QBqqzLC)9{D3t{j)26*{6l5J$l;A8s%9jfFeDFp6fD!6u7&AZLJ?qyD|Bbk?k>*8E>ISo?Kc>T#Vn*5emO=e|er$CWig"
    b"4ux3a{zAuHnX(5jtq(jwUB2Nl`^cCP>`2F%xl;^J`&gBROxA+cDK2I<{e2;)@hcw3hU(a8HxVbA<#4wk_WPboIS4<WXo-TjddQlv"
    b"N8(PyjPj0)AY5d<6!<P6J54vQvH7!jhPvkV5L1gtY$Az>zi}=?njzdJczdI%z(&v2$#|5y$EI!%y>>~UYPBD18#UqH1UO~dWMOFG"
    b"!4fMZq6H)BB`mL?DlQ4E<1-szgUo?=x{#ZR6yE6nApV4L&%qB)EZUKdv%MZi#((`n$Z09c-d|lUpoy%Hw;_s72XqOEV3tSGxeAsj"
    b"Fy}Bp+tgfEw2uDEixrWBhPXcw-~X2C8UWq4+w4Kx%pbKIKuC>hHgIPm8)+2-qZ|E5E|h~ZHOLy83h7*~ewQ*qL9uU#8z69SySTqN"
    b"zQ$=2Kkq2+_ob^=?!kI1(-4%sWuw7E3?i_rWkroZP6zavQ6jQEX|ZpOCQFLS<I&Pe&?2dD#|1lyVrRI?iR%uh;}k0J%R)dpiQse@"
    b"i!&50)d-$IBT7}yH+o-`r3Tqo<|qk$(_(;4PG;k9dMd*O)TDm$TBcKK7{05)lZfXO&Bud6^bXJXtq<%Kj@4IdPvCLU=GAs$c{++4"
    b"wEJxp4>o8w4G!94XU)F`_|D|rP5m7goWGSexjU0%DR<*aH1+zoc_wb1KsrCq{#9_|TT{Yn9Ud249F4G+2I=P#K07cYF4}SMO8V3L"
    b"9V)c$+m_|lN0T3~S8TggW9UQ4U(wj<(A`rB?wnb2`$k!&rXW>=a1nhs=PPy!wMjd16nVQ?vM1wQ`2>B&{{Q=RA>;c^q_V#of_B1*"
    b"Mqa^9CMVARsu34_%~!?#>cwA@@w-2tyz@^Z+24?i0{@otD8MgUJYwU;PW4>w3$@`|ucr1@HTfUoC9>wc966CrX9Fh+RkhNY4sv;c"
    b";mn?K`|P$UyE_?;-i2q(O#cCB`g!z|k0E*4NiMUk@>Pw;@vDACize(ptsZ;vu0R`iN0;1QC2O;H0N&`;B(`JYglljVaqU%uiT=c%"
    b"ary30(Vd~%E1$5obQ#GF@UeC+8~6uq;%6ROJ{tWnXm|YOloAjMx#>m^d08><%v#e6P40qVlWm_Ue|}s>X}f1HvEQ(dxbIqCEsG{O"
    b"G0g}bK0kw(%-~ILJh@B8+l#;Q+}T#&RMKuVlth~o`4p$w;t(Yy{S(+<n*7R{^>vlqeUM3DOt^jgU}DG~{Nul#hUnRkoUY48rVpEN"
    b"M@uZ;g0UIAFTDO27h_3?XY5#(xM&Yrr8<$WkJbd(QZfZ#PRJlZPO4;pLNQDh&CuuM|4{w{Z<0Cz_bTdLI+_#;{BPsgo<Hq8ij-1j"
    b"+}GX;-FZES*>B~J_;|y<^FG+GKILkgy}!TBo~$_$d;^)G|1SvjCpCu8$Fk%S=dVXEGQ5eS>F$H6UsKuCKyZ0~$VFD}Z*z!a&n?^9"
    b"d2_;fC^!z1eYW3-cA{Mi_Ep0bBBP9br`n^R%8_(xLUs1gFQtBH{Ikr<@FiHsWyMk^pTA?Zw;gd1zk|jTceHSvt}EwLTfI8=AIXDN"
    b"d)TR8aq#*-2`?^X_$8M9oA3Vz!Y{e{D*pcac1OyzeG(qK;gp~?52pTg;y+s7YPR1mZ{MH2zNtI#jA;6%(l0>C$5Ul^(|B15V4<f6"
    b"@se#$x!K6zC*h&TKJKh28IPu9#iSFMp5Y14%qXp3yb1T4IOOxC<|=*C4$iwK;(eF<KHeQolV(z5-p8}fLm!LnMzciH8y}V7Rxe1|"
    b"+qG{yzh5p)pJveRUOxWVmS=t`L6{3(1Tp(Zj-%Jt9ZlXtJ)`!NZ|9ZO|JpH<jKh1`c&P(7`1E;glX}J{Ur(efQvvcEb)^Om7+h3B"
    b"kzv4ioO4VEe&>~Cq=UUKeVC2sTyV0Dr1A9ho4N)63Vc#z#m?WUm7RVKLh5I*6q!^(4(WnzND{^u?!de4FoHFmZIybMUtktZuoEj7"
    b"O{Rthu-ZK2xIiKiNw)Ri#qIKx{%^9){u3DUCp)re;I@;IoQ{(-@T4|z28cCjTUT&blS#jFHnCZGB4Ha^y=h04B=|{SkMzMCPfQBi"
    b">~ZP82zSsFqqnKwM^l_O<#Y|Bw6NcblHf2U(xge32ldM62n25nsHoD+k2E*-_=oM=?3;5FIZ-=H(~OZVcya#J0Zbi9XS6$PlDrKQ"
    b"gZ}};_4|GHrC?Hwel<ArZMWoYxZ3!h)aCpY%o`nvGgcn#x0AQv|Na!HtIMbMl>gk=)^WYUCc&>~?bpIn{)gn`*Hia#OLj+-R}Zv3"
    b"XHUMt*E}K=ja?0XGXEx{<-hE1>bUhCo^<>+^;aJ_c(P(Qj@qA3ebXorgGu{<{Q{DIZSrxh=+osv@r{q)YO~|tUTb#zG&(plehk0s"
    b"mr*5UDc!ydQlR^J8>ZsPZPgtBMdP1(daWbD`VRZ#)<b5;pSDf!_bPrMF>1kR>im8Ovz`4VeQYT*DVqG$^$oA?9v`%SWyLM~PthJ{"
    b"cprZApYeO9#tlgE9l8#4gUK5u$6r*h{)+eE`aZZ5Z+ac&y~AGk?4bS3ztG73Uk9fLsQnpr&qP1K{b@Y@{|eg418p_$*pqFx=+6DR"
    b"^6B!~FSOaO3~`=~eM>)_#!HrTOeSTrz#-HrS|@7mM*ZKtONZ~-8P)0hyWYOhbKK2rwpDg(<f0}mwU=+@JuBaT;=>tz`9O3$p%S-4"
    b";Zt=HG3fBIgHz@DTIKuBfQ3ygf?4=y_q+BKdKPU~*w+}3aN@@!r31>6;I)64E(xAWqCt8xW4R~lYLDrA4LG)8&RR601ai3IxA7@7"
    b"fl(1Wk!X%4-|e(RA;nu6K6Zxlb8vHnZ=QE=@Y>vwne+Q>bflb|BKCOHxsPqm#`ih18D%)U($B{IjQI>=*Fs3>J;U2(RSSDOejII^"
    b"$<<fsYN6=QKcC+3X!2Zi@bY~7kNr`+?nE8rEv*wx{zW;JZ+5Z!1mv5G#_gV@muD}$%r9hZy|iNo1Q1{BxN-D8L7w^vl1Im6$4C_E"
    b"_F?<K{jXqgH8XFfE>I|SPOcIaT?ZSnXEuY2FncK7(o^JgS2`Dp>S#nhME830YyNI@T1Dc2@An3wCd%|r;%DGnBy0$+o=Bd-^@hn4"
    b"=h3cJFP9rL(=Me(Hrm6<P6H{~1UKfm<KG!g>6aAVE40Q4I(j!T0QanMj&*#>;C+5>(!<Oj^MH|=ETXY-ppJd&Ve5-N4L3yT)N7-R"
    b"bH_XEafbJL>@t+v_OCv$6D`{DpnW!yR#V~psb^Wo7}h&TOX2NicuplV!<*HAj&+}_`28Jh*}<P2{a&haDFL&h_DIA&WbULi`6q7A"
    b"X^>NRW-6b`7l%-4;un>5Dqp%dyK<wFnL9U<`l3eCbajg5gH1)auLYY@NfuE`-re&1%K~d3D!Tag^zl)dEt2`yp4A{tw!#Is^7ENF"
    b"c9T(thsU$eS>KzUYJe_cA(f$={b($B6As3EW3fK?hLi40Oz<eMTXx=D-U7a|6-s914B8Xfj#7m}c^Zs5saA(|*0;}c5((H3uuxlm"
    b"v4hmX1~pY3?(rL71p;!aL10s}3bUlPlorp}&x;gInkaUxssQk)JqCI>RJMr_$OS)>f#*761QvqIcvuY}-pxP&TwaEE##6`TDLpf0"
    b")f76=0T=PkYC<_xEW}v}h9~G4Kh!WnaIfs*Yi(MG3jH32=U;A|hQ)z6kyvM4rBsHz|E6Tw?Fkla^Q;fl`vzIEPr7hAYFp`iK)1^!"
    b"4cd*wPt3W!zzGXiBA&YH<ObPso=S5|;P0fn@T|bm^AcYA1TIeR|3>zRTX4x#OxRtp>S$;#n-wDY1(pwWV?%MVN9RiTT&?QM(quh}"
    b"PUCeXtrD_TI`?yS3&Fb`)C)kLc2%foAce}D!8>f&odsKux!oRphdST0qajZ)R*qy|rrG+o21qkMG-$`~!rDJ#BcU}}TR__yN=-86"
    b"+>OTo1)nOC;yitxr%)y_NtswoexEMLWkV1{*Zz8d8|twqvU5s)HzK5pv77uo^G!`N`BZ&%em(dXa%%BA-aK=MhscDEOMMN^T_{P@"
    b"aiQe)OLGUxKD=tjg_*uM(+Mo_bAPA$B~BhJWwXQRMqQQEZ&D8%n!7s$IkHTDz`6??xgCws^!kQODWOdMBI(UEyv+J#8X=<iahZ|*"
    b"v4~1(kFlIJZS)ABu_O>h7A`-ZlVr{5_Cz<O@ywg<@4Ao7w{K@n;|a5I*NQ#LW?p!g!Ct7`pC9)?th06uXy;K7NIRRKEXn%K|L3z)"
    b"JnMG2c&y*ykED6J>5BW?3+$Pi_@(#{*GC7Bi$N1)5(x8q<>Nal5-JqLIzRRn0M`I9>Ic=3WVkeM{>aN-=ak0BQ+Pw%kN<AfKigAm"
    b"fsUnr6GD8G?W^Waxk79ZcOjMA;pDC|C}<@oTm@|6G$p(Nh6JQ`HXBLa##nyse|0e--`NW<HJNAa#5U&uMz-14aJN^8JvF%pg?s*S"
    b"?<xxI@-uZyposM;LcH)M)tAE4<fA!9&VcT`BYdBUgQ<1B1^OF*?6*fGyMHX+G34!ui=p|0hUWn%OHjGsD)18OtwKB>o~Ne(DSFdv"
    b"R$FB#piyq)dnOY{?6mft(SuVPWpMke@G!fZjlvP{uHKRJ+lB^LcGw@!x(%`dp$Oj!)U$V28Tky2plAVN=(8FfC&dp$+?cc=px91_"
    b"n@Xdb;Vlwi3(6}}KhR%vaRJ&Me;ohldhYc+-NUMjIQ6lx=6RUzH-+8NQ{W}1b%C!Vr$NloQ0)a-njgv!r*D#3{5Kl`a%RCgJUkM7"
    b"r?9E-dyEfJ-?d$k%;~J*fM*j0zYx;TK*d2rM{1H#%@NQz8ce4A7S)Li3tKu>P}}8oc$7n->0rRPp+u9+&)3*&KoLA1Hus6DAwpf-"
    b"I&}|ET|8yoJlu3Xx^YhXan^iEgTl@^0;qa7?$Xk|Oi&~`rX6h5za042ODJVGAiI%<wa#mc3wZFdW_QoSM)>~7$T$ll8l){~Xh1rP"
    b"S;x^%1i78+eo8V{-#FBvH}r!FVF#;_0)Z;|YnfsvtoOHyswMXapr}v&{(3Yx-J=BYRK;Hbow%@@nS`CGlxDfX3RvXXmB?AngjEV9"
    b"&Vv;ZNUGUs-cbm)ta<->Njm=&=Eh~jn?G7y(>XY4Uv0g^jh(a|nAxN*<ji7acr>vPp7=*7YW&=)I_|eGQ~I^$pnb8R-sdQa3Mjiq"
    b"I>`&iz27y^{P+W6WCi_<VO<a?i5cbVLkl~bRp$auuh{pS`BITx=mE|sea5{MR=#J~$i5~f-+5D+KcUOBemMKP20AgF*}<Kd5iB#|"
    b">8-N)=8(8&xVag4q+XBIv%|ODj@hq5R6Hl>4YSm;DLb+5=Od>gsWH1>*N^7W`@h;fR%^dI7EPv1*Cbp0+U_oh#wU9NaEXuIR!zJc"
    b";t|(_=pR@wynHTLmz=$u%z|&eIDQ*cvpkr}F(&3wUxWLBt|{Zftb<W>OA_NOA7P3O?H(X2WB=;9oo~I-GH<@4m7hEn{F$gl-=3`B"
    b";rA?DzDVcDgX81f6tvPO1qYCCuPgg)Z^D=wkeva1pq4T{oH#o;nfGIR>7@JW*!krr&qkkO-E}>=KY{Az6`ddPZT6_$J@HMA=61ek"
    b"_e@ZekJa@!mWp{)`mi}+j8X0&Y7=L_J@TI7r0pL3q3_YvfoSYPzO^RS#J*R}eJSoX=F)#77X)i1waeih=p47}KR!%-)|Q|&$g%>d"
    b"I|h-pA4lyQw=Ly_u(`Ex;+LCu|K}DZ{wg1u7Y@P&vE2uKjF4}ZRYlw|mwrV0M70zK2Q&g5$(Kim14=Ls#XDJEp250R55Q<=PtqP5"
    b"v9C@IPEITn#|{g5)~h*TH57zfIa)DEstZ~mx}`I*-)!r)nH3g{vDO%*!@k-!*};+q@%TEffuSm-Jp%t$6WvySabfcO5j1H~@LvJ9"
    b"l~63-NKH;c8VZtx@^VY(P^4J0e4%J8AtV%|A~wp&IcR{!^Q>~?5mu$_o3u^8pu#VdrjugOiPDaDT#h@z{XCmomaGaR%Ex_XG-e)Z"
    b"{`F9}Qj8Rud&qGqpcr3|MYwo<lRbiXLE})YMg^BrUtSK2tU_h*g)X5FS?$7&Jt6dciVQA)kle}(m*{`s<ppMxm_dzf4_8W&`Q{U("
    b"SgL00OKhsDZF{3*lY)3FDGMz5gC{h(%qo>e&R&7dBZsH@Hm_wfQWrFUgBL0_MmX6QIz+6;b^dUqlD8DI1`>Q+GJIx@21*Bu!{=QN"
    b"woV0|w*QaC^uG&n`9Gf;X)Z5nyrO~J;Bi{F=SLwfnLbGJamA=1R&}p$JlYw*YWQdk!G9r!wNDT#?GF-?<=%Y=9U7L=eA_C5Jd0D-"
    b"Y-^$=MGYGej~VfZ=c5t6oftld@1Y7p^bHixjdp%p2~`+LzEwD%V;0*Dat#ZDHQ7`D^1}N}mib+*z1g=xd~lMVHV|Zv!?iD<|Aq7C"
    b"8s&H^p+fp&c(A>}Th-~!A6R2_aD9k(V!;~}9(!W^BI%?jOB9nj?`Z*<9KW@R?;Cr{U~`%sC+*eZa{!0w4K7?{l*MjI=4a>)GG#XS"
    b"syaP6R+%x*pU<0U8c@n9sW~#juMG2=Q@Y^b32>@KDC}!{(VXd#((yE_wfYnH=mKLE?Gr*l`b!uZI5}7EyoN_gukbDWSkHhGGReNA"
    b"U6&tM%wqE^DHkuW5cVY0;QPxPrV9mfdj8!`Ua)C3UZ$}MF61CYwNT?dIk&3QB4!bM3=v{+&F)aR=!4`)lVS1;U167sO35Wgz9dWY"
    b"G~bEkwP}l2bbsef`-OAf2D*y3+*{Ycd14krHM!{Z+%q)9=%lJTX8rYbrqcqxwyDX%-lR&FTC5Qs2x4^s%e)L0uKD4q+JYxhBl(`N"
    b"qR$tftyJI$f6b*<LYyB!JTB>3IT=qi@8ks;$Z1~o*va}|R76MY;1Ie)Y(4kG6=zZZczko4;;5pjaL3e<wnSqD{d-TL@f0fqWCI?="
    b"Jb%fb9xjFxJ~{{b_y*3Ddqv?l;_{o}fD{fI-|bA0&ar3Vw!nr$jO_lK#+H999t%$V01kZgZ;45D#3&>!;<9{wk?=FOSw;T4V0`&c"
    b"l^)4hKvVo-<yq2oDY-*2K%zclO^gLnr=($3#h;(tog18=aK-ya?NIrZ!*7l6>@j?d3w*Jf+-nMrl7wV_ZJ!8A>`nSOMED4|HP4j1"
    b"QvAEhIaQ%cjU%xY%OlFrSP93{b{;GL=T}SP5&hia$-#RMf2(@`)nmp2(t?ZNEAmfD2IBFWFNp_Dl6W_XT1zq{%2h|h-$3`wcft>c"
    b"pzC0B{**oO<ScM;PXvBcS(=Pm_Q%l=rk3yT|NmMgqcRr9jUcBX)v&KEl}8jG$~htBkZJYgHhi1Jc~hcWNCh|9J>t^K4bU}`ICF2+"
    b"4JoXek9T$}!Jh=j6Rcds#oG6CnL(=slnZ-xG|Tb8Y0e2=6AV59x4_ELq>vBZ2a7ipqr6Kq35gv0d}o5U3XSEYk3U%%UeU6|OEoTB"
    b"V5~$XjrzmOTXULuYpxN5)ey&%wWKf~<}Zl11WPoS9I8RWG8N-<=7TVgpE8c%37HapJkDE##=+XSkMW0upFhvz)!^52T6n)#|9i;8"
    b"HJ!*&rLYtdPjUFQWQfLG#B<i?J;56C{-MZ*iadm02{-vV7yj?WT>3EYpKYv$^PD*wmhjpfFK<>Nr?rDlPVyk3Q<o!<c&>>s6e-?W"
    b"U%T(oB`#0J)dHLS(G712y=-b;C0+u$Aw!lv`+S_I9&Hy-)#s}vb0bYXI+_rc3>0y<VCE?~Rd)IN9CRel4;N-RtcKHiLCDnYg?WQR"
    b"lg;0HVpjXT^dTrE0t5uV5)z&j?kn|*`hpXm)4vHD_=s#u`ZmzWcuUXlP4LJX53@ORhul;U+KZ4s!gGnnMO?;q@@yHnBb@mwdKkCN"
    b"_~S(0fRvDud_p==^y=sIDC|SU(C%aH1&Q7AbZwGMC?*PazC{^ES&uitZqZj;^O;@+>G_rvyDZN#gY*d9M=mhDSpo5~@Bn{HwC0*i"
    b"^?%|J&)uGDpq!DC<39c#(vWYug~#}l_nF?<V-l<(=cTaQ*e#rQ@WjwJFDUJ+=svoKT;M#Ml^Yj-D*cI1l$ze~=R23eZvKC|wZAj="
    b"#|^2qKggpV%STyR!~6d#<f4x)ZugN38xIT`m9x(0Bi<>|ytgA+G-SVNcl1vtI%+Of-s^qimxDbUo8p1McdYT@!>*Hm-|>^0T@|qZ"
    b"M=#j32fGr%Zyz2WPkur9_0_S2lKAk-xF@kX@rRzMH#l^4rEM&$TRFO0dgY(vL$9^IT6pH)=4lVcV#Du0^-lBeU;O8)?qb)%FL##b"
    b"a85YdWu03%tJL%PR~PjKT;_*MTGhUtudX<Lop<#dTfF)!;b*Rfwb`tC160XCjjDxH@5=-VX7jy#Xg8p@DH-Vr$hyZ90cSSYb4V!x"
    b"^iWGt+odXX)(ZTP3f0C>RgpMT5s?0Sb@btLRmWfPSAwKFPkqILA+WMciEd)AR;tEE5~l|Gsw`oj80epv9QseHP+*An)e#np;zFl|"
    b"YoKk;bQCS<A`RW!Jvx|FsvyETwBprG>2f;16hqF@1^+!IE2+E|J&HVncxVc%IyomujeB}L5HMUjTfj?Q#HtKK6@`Lcq<7Y@T&);7"
    b";la(S>=BDrvVl9P#9Dyn1AaDlITQ2{X7`3J3M?8MaPT6mQ65_>!&7C0OZ7AHqn<`@-NADylw+DFJsLWfjS~+|hqCVJ4G}?VkRd<<"
    b"_{|aKS399p)|SBKceCQF=8(T`MY>fpMPHm9RfcC(r;}1>`fWd7S_(N=pTi$sTrKL*LPb`UOxU=IijaVKy+FR#4CX4{bP61)K+18|"
    b"k<2h;m2^3HG?l>MFJa%Z-J@+P^*x+!7OiP)iwZ1ye0@Qq(<PF|=ypy+LUDtj5miSy5&+p>Ra@-Q(6t3;at(i4ZX~9bV}P)|;(p2="
    b"9d%YR6@dpJAMpscg7@DG&Jc1==`>P9iUf(xyJt1yGAp`9+5wprM1)uru$7S^s-f+P6*TVjpa+I0r0~GcH&>*R%FyMpQVo>_C}Q>-"
    b"o9pav=hK0)G@i;br1KP0*lw-tjq4s~z>*^(Q6DK}SJ>tB!2%BNM;=X$k{9F@9#Lig;!<$NLbLs%n<e;97Q_7ulu<DBMYMnm%Pd>0"
    b"P!cIrN)Xxr8XK-2CRWuVab+uO-_aZ>76ZCda;BAgfKgN?;|h6B4|~cU{b`%aBZQ(?Tti%Z3*8T}-ZY9K5OYSsi^M*$=@2}qi{-T^"
    b"ce2UVxKSmgWmOQ4GQ0>2n1V+obp1{b&&MQ}B!sFpek12+1x&og5>SD}&_$3Xa%JrMc>V*T-wUSY1up-RGfrHOKzI=xg@T3(XJWWy"
    b"B7f_lqFSvnr*UT^)S`D*tmzSDyu}OZDsdr{4VG6O4-R&BjJ1~SpyFax&^~HI(<mO@a{0)~RVJ*v>^pwsgH}7<Gx|pK>MOSlH~^%3"
    b"S3b0cTv9Eobkk5wL@(k_d}kIy)b@jC&ETKy4{bYWEFGmLvAr>`@7LpYbZNW*@BeaQmoG7BTZ&y9ooKTA;DDjs)JmEVPw9_G_@LQK"
    b"`&s3tY7bw6XhP#48g)V#9myb5l9LAUrD7UMBpc<LMVv}mAG(a_reA(+-L+77`P)r<&(Cpf>51pH{rI6>=ohs@fn_ZOEmwvr-mGTQ"
    b">AMRn?%zuIFLsertW|YTszo}|(3GXKZ1&a>1#%0HJT3LcfBizI5jrpQ(6~`}ly`AUfWIJo(=49z$fLRE55)joFp1TeE%6SB5@FLU"
    b"mkzLzYl0`xE*k{6+u&<wcoe?mkvh*_{oq$dC?H6e{G^b}^THBfZGg?-Hv5{-s(KRIoxHy1dAud?)t*K!aH`M5&7}8)OV2U5B)Y#4"
    b"r2KifuLVf|#EVbWquWX9G>^*756~rS+M7>PJ>C#R9?k{ohoztw^VG|OxBhf0B>)*>J?U-V#Me39CD<?q)FSQ^m9evNT<GHwG89<s"
    b"@pJRrTdqOX)&B8NMTgz)tBCNV^HEmOullHWCoGWGBO`Gn^jCtueqP0Z#y4`rL@tTkt4KzJ@`_y5dj*>PkMAaB0npLf@l-vkl1D+L"
    b"TrbLyIWSyBBLPo^e~!=a4pZ+El=TH7>3m)SopYf;5=6dz4JALjSC#Y?(rYfA1{V3C+C(=~tvRh7IUhr18Nn@a2K*nw-akHy>q_)I"
    b"x2n`tGNrEO$Cwgs)Ggxy&pgL&A;z?fP?vzgWS?W0nS4I$neoPrVJzo8k7=U3(8NN0o0gH1QIIC_zQ~D;Na8o1-OuhD9M2o$3ARc|"
    b"k>s%~X(!nU9y?G%j6^;|P{|^wgsQ9d-0B|^nC#;Zt1WeZ`~IqP&$;K^bC~k|IPhj5YKBA1@aYcLwh{UjAIS_8U4y=fn;`SAp}t8>"
    b"6l!|2=&uF7Hmul3jZyJzq;WuRx>y=v1?*7V84y4l5_zXtqWX$>G88zz#Y<l2<5{4$2ItAYKnr^#5Gx3Z9u?)dlDI$oIcK%;@|b1r"
    b"9dY7&jW7r{eu~#A+t$mV%wX#)Vnk6O9t?75J##!f>|NqZ-&B3Te-$N{RSTv1@AIcOZh^rTa2kx4E0S?#;iCS0JPa$`F3!Y78Ck)u"
    b"RB;Qe^l0O(RYGB(x&loco<CiIyvQc_7fE2dsleGN6ZFS;qw??JA_Ye@T7pS}51PIa!u-4ioEbAxrb09x$cLP01-7X68XXeRP`~~)"
    b"o~ISOu5FDel!ezu*8_j<Aq9-bL{?ZeNWtLEmf9dbmKoe}B8q!e;>=6NHe&_RHURJ1q8|BT@F`r+fumfc^Ag8jkVTZxjfyS^q8Vnq"
    b"I)!7rd!GmeTXm!QjIYVIQuE(A9$-95eEN1Hb=8mKNBUixcg=leR!A>-B@PMQW#!sMoZsJj*nlR{j8p)Bqb`IG=6$D?#h&)iu(SVF"
    b"-^ik#N~Nicyb|O8B(%y%KJRDwRr;L@9*i~0L-%TawlC{02MJl!4G3>HaIZ5XzXSZ53gkVuA{<Jm+e7a=8d*D5O}DyiBRZoHvzh3}"
    b"boX!lIC{|ch$XuE7A1Kf$^#VN^au}$ps4MGI7)?f-gv!&5HqN7@h0SDNXv>}JA2^h*yPI1ZdscF5dlpEauql6=W)N>#EQx(EDIi#"
    b"nD>g`q|iCfhv9+<`ygBgEO}#ut;uedW$!;CPa0Tpt@Xm5;|lyycdRi@Ig=HP@fo<yJ@2*8)R?m^>BC*!C-&p>HjmqX6R&9yul3SZ"
    b"*~}A=Vo4LW4JXLJu01a%RSOr&uJ^^%59rq?wgf)5zP{C-x8ELp1o(HS|7xVyb&lN(qUd}dwa%V-cjl+rxvy*Fb=eC?nCWn5+?U*W"
    b"(|PP8WBq_I{E$V=D$t(zvcLXK{p+Eu;hlM>a+%MU{PEc{rOpJ}AM>7%6it!8n*zwB+zu8Mlx1Gnk3eo1cwo4;wQnWv_fH-k*;zSs"
    b";u#Y*xsJl(v-)sh*Tycny6f_$YejfRk3;X@u~g<3jsYvzkV!eD*JW2yt(1FfS4YQ)KC=DWG%D<_9ewFv4utCmQO^~7m|KB#c+qSD"
    b"T=P+phvq2LeBvzG5mT4H9geUq{Wwb9Si6rcZ+xbAxhLiGd&)ZlamkXLm;Rw~gZ>;Y3ANoH5ae<%8a|jn9_1Av3)I`U+X7xh0F6iD"
    b"xMwi$`-V1Q0Dt%;19#!=8RKIV`{ffK+kEYPVIR8^zO9|5_*A`c(igl$0Qjtxct)kl3SEVn`jTKd2xwO>Obp-IK&ALQL(|!e`SBjb"
    b"x^Mqa7K~`{Y#lq2`F<PD9H&;|5Aqg^Q%!qSU9o-a<6#Na8krwwHb<%CX)>HdaAaY>J}kSu(cc`iR>m()snPOtbxhyir+IF9rtEPt"
    b"s2rr3ewJhf7PWl^Kd5JR<cg|$`BCF4nF4Dg5AjL)kbYm!Ge!!klX{rlyWEpgyYq(?dBvOY;^YEUb}n;+O2rDXam~*`#R2eXeNS9}"
    b"bepnGkLz4gi_iq`uMWM#OqyoDz<-3;NE^$TPD7{{=xNk3J>$wOd5&GY&YdfAME1pLXh3Sxeegv!b8*E`&B(}ppS_P674hCIbD{)6"
    b"7TB!_h<)Vnu)PykNr=7;hZ?Yf_wCf7;Z`o-Bl0^*2>T#>C`iR7cEK=6`iZ{KH5%WP{jWgBgZnQn{3y=)A_y#-LT%_Hm#~?|p$cXo"
    b"bO~P=D)Z9j(uA{$W;ih67sLA2Pk~%J><}7>F3gTae8*aK`U3EOx2Z4gok0lqU7`VX-%*MN4jDqWoQ8$IE|lUb=liEzc7<@xF7n;4"
    b"*GFsS#{dp5;Jd}@`JVEj*-n<Z>qPGnC)Jl?6$?=l`;xwQ))k0owHndb%fA7OUo_8!^my!}EQ^IVS#BOQ-+Yxi*<8WwlE!x`Z;9z@"
    b"XDmHP0tU+r=CVt*mniO&G1oj|@11c`OFh^7Ud;U!)BfgWY}<C78n@4#U};kDNk{FFSqw7p(R&j<GJso7?GURiIm+Z*?}16m%t)LH"
    b"Q^jARtP6l|93I7CDm%oRP##7l{8jsYwvY@7wYi)Hq9Jc%Mbp7xi)j5g@p`!~uepdk@e+y_W%f;7l493utx#Z(=-NgsHS`_#2!ww5"
    b"t&|gMRgxihaiZ@(8x>kDxCu)Z9t^<1E`@KHN?i$}oZ!eb2?U!?LWeH84ob7$RPRkM&*$RUy!&^Ta-lF6UH3Qs?|1=s&JmP(`0L?E"
    b"Q2zD04?-aNILh;eD<2F5fvz1Sjz1ENrJ=R|{(Ou|@4U`Z@iU$~ih8s&iM)jyH(AVamho)l-5QR0p|xWj!3s@F%$^YD2iBiDvA)0J"
    b"Ne5Nb4$!u4NO=Kw7gJe1<^Cq+Fy60ID3-tMUdLuy-(}hU_qtnA@t=2XFNd+4HDG;3{JRDu4-Sn4q3&U*dsGZG)Nt^xKCX8$AHYXZ"
    b"d3W8t`06HW^4pU)u}${dtnVrJZBNd-EXfpp;R{kt-{z_e|HI06x<)IxhhRSLQ=fw!a0_<e26X9A?}D3cWnbO97e9Y<@jW;7cHd1T"
    b")xPa89?J}K$>V+O&biJDQdF;glqbi(oE}E;^bkKk+Z9~5>j2oRcotxo!iU(t9&;Q!wHNoGn+y5&x${rIZ7;gNOkvx`kk_l@AkNv%"
    b"xEO%^11IhL%Z#qD%TkXlc0H-?Ze%yeSbt+ZI00_Vv2pit=kh%F22O0#+cQ~~W^Tc`guE0B*2MNDq+#g$)f9w3mtjdZ4z)Q8rK9A_"
    b"y(>OxgWg{`mwJ)s{*Rc=c)!T=zKg@?PB(uy7oUWG|A77My|jq^PbfOahlY%B6Du9b9Ro+3or2$MRr-d(3#i2Y;!bH>u01xixNvjP"
    b"<BhVh|1P%Z?UehDJ98<!kTOyp?`#6Cc}IbO1y!#A-wk%@!pNyte&{E|qQ_(H>qXw8J2StyFz@wu#&)w=_sGoR;(p}WkBqqstbLwO"
    b"8KrB)7NE=87<mQePO1yvS}}6|l}{h8Xya2EHh!*kthd+BX04g|xdqd1PNlwU%4~(q|2nqtgH+Eu)+3WFjtY4<v)N=skMe35PBd+-"
    b"eFatws+Mu!!_)m=SK8UNGN&ii<EG|gDTfXH^jvlx=P31>d&9<Ae`Ds-0!=xKshl?+d2_vPB0>WZXd-79{(F+f?_t|%b?MoD@PF<y"
    b"hpXgLs>g8`V~q|r;L!A9c0Ppz_^Nx;$<8~yGqJ^~XPiI7wf&nM?`F(>3XSCmiePg3L=tqNk7KFikO#jj>`3x`r_HBARMG4@)XvT%"
    b"x2#(+DE5sv>xy`MCj0h`A|5cw$8;-f=QShwP=%tCuE@&C!}=D13%7ke@LtQ{aXyNoDi98&*+shy?5lA>q0)cQ_rL}deoh?m3hr>B"
    b"J~a5}XIR06%31zq9g3w7FUWGU7m*~^7!kQ*&0D`x1OA~Ymd|f@Bpi4dNUL2JQid$ojER$W47=1n!7dgkL#}Hz$KIc|anZA2n?BdD"
    b"Q=y^BNjv3e0sf80AR@0?^Y-sa;MWU0RTTSZ^vB*wmyaEyeF^36TF8*De8Jk#uO3tj`#qOCVnaC(dZcXnF-XeCrS}vGbp2~+B&eW<"
    b"1Dp6hBftl|>yw4ldOoUq`==KgQ}Yum&-0EW(E>`eppG4vhoVx69gxn>wC##Zb@6!L1gokYWU&TJ#V9%{J$EHLW#NMCATJ%8D5gvn"
    b"4euBcUrTXWJo+O!^ne~!Snb`qgDmvS2Op^Sd%UICIo@n7RK8M~cOa9R$o~ZwT-eLjcoKK!INAjp+Wo?T4d)Xpkr(a+5q85sAOITN"
    b"5ldEl#XcNtILvwDpbKFyd0(!5?1J_N$tP^CJ|8jTd|f0E5t*hG2sGtxV&*bcnO-uzT+|#YkrJBP8xF&(Xa6HRH_2&}MV?S84L%UL"
    b"uOn~`_y-dB`3EF+pe*DRG1=3`e7Ra-JS&_aRdxq?9m?}bS(nx4Aqn;&Ib5b!tdWPHj^h}Qskvr=lf9vCmUGS(cA2fuitz@s9`rg9"
    b"%?Sng<+Xm;B<akh!odpNCxrXYphkQ!A;l}$CjStNUn~AoeX^&F0t?bpqhVqZV&(69J-Cc{T44FBlzW(FJ2Xp6?XMlVkke$7uo;$>"
    b"HS`83c74MA&56^&Xn4O}M~Ox>HfJje6PKHQDWuCS0_gO7jRL{1#GmpGbx}mze;ZH54=be45h;!0&{-i0mZ*EYK>o-%P*?$SQXpwV"
    b"XO-}hpz4LZ-i4)H<oQY3UdxV(N|6V!FUON|n6TLH`NON&m<njTYEdxnPeS>{Vy3X$`s?v%Z3yTVY-kdBPvv>xe5f-^;1LM0`$A+3"
    b"ge@Hh*hmnvfZN4?!A+*4aL3?XH#TR7bG#;&uoy(`Db~JHZ~P=E+)Enu{@aYw`Yp9GJsf6133Wue>$S_%D>WZ$-&$xfB*x<cPb(hJ"
    b"&wuvaHvcB=(%7l9kNEC-UBDpqJ*Z&^*Fw8dhpReNVm$3-AP4{Y&%S$+yh)?sFf5=A;k)almH4;nUF6AY;akQZ^SCNRqp8&6-BWRw"
    b"x06|#d;s9WE)h1~omWQiT>xuo+I);>hl<8iJ<LY{>+Z^%jG92vRQJKXm+szQDEq!hk*A~BKwjF|r+5o$mH#gN#RZ&z^gSO5&5?WW"
    b"Iv<m-LJ6xRA<{{fBoacz2;>4ng5q7~1B7U)Nv(@gU05_;taWfprDDa5>%Q9m;!iqIG5G-jImWa8{>WfQv)H~oZyj&f{jU4VTViYL"
    b"j+nWV-Mz~yAeWSa?h8wGI$Vrpt(X_WKh5G5#$2}nbyNaMh-dx%fgv#7aXpZGj{JPqbq>wE?YgWu)O=`S8Wnjo`s&FDzAvIL&!4$8"
    b"lt73W;#ukXHw+GcD!ifQB$^-Y)?ZmTAdX;n2E!<agR-iS%RF)0AY^9%>aT_jLjSdgPb2T&PFp-sh1b=b<Jr%3_=poAI&a1dNF-AZ"
    b"D`l??H1e#7Iu8*8?(*;SA!>DyK0O4EVe`<bh(<J*WAurV&%T@0?VatPWjt}!UDpfU2}XxFv2QKyHL-p1P^%fq$v;`R%iAm9%6?Jz"
    b"9AtNYK2Gl>S3623;$qs(@iJz#?6>pK)~gp;$S6vY-n*{ndNR{1PkdFRr3vKiQZl9*%E^PftiMGKxY9?B^l>?2gzhR2biVR>Ozdl3"
    b"i+dIF61b$VmV3N=R@~+7AXY?T7jSb7(~8BrKX1hR2XUflEsiwulE@p*jh}QEUUouVxKc9;vcC=ju^vYt?xNj0OGA#vye9vS%Y@g)"
    b"|HgOTE`t&y$%BPlE1l;pTJUg;g@TJ&*NUO#b;gCG@93oif~-Vxg;4@f<t27tZqJ<L7gDe_>n_gct|xZPx$Xr%$Ma5K)PNUrO7c6M"
    b"FdIq}R4#_XET!2>*R8u>u@xM)lv}}aD42#2(nE{u#JNk(-XU{+D;k7JKDU2J!C+|4Xa={};n_LhgzNr7FoV7_3bI%!ds>y6KTldi"
    b"bLI4YN`)8|Kdxvv<Jy`u*F62+m~)2c8uMBb=3ZN=LAa>e#V-pN<pPg*ia@xyzr`)@{6{zl{q5r1nP(2a)5Tvt407=8T%K!-iTzbx"
    b"$qvzF+0;So6od+RR1WJwH=?mC48?;fvwFO!p6UU1;Kt8(vdkskFu8LM4Ox;`DcF0H30=4sKvEJy#%48~UT`D8cq&xn;;_OwndI?k"
    b"xFycq3c!57G?zRV7wh@LW?c^}BQk1YQtm!$L^2?hJ3JyP%Nvrv$6w$P8m9SC6~d*SE|Af~x!XYO4Yc07W-53Q)KrW{T6OqeQx&CB"
    b"oW(HckSkNX$MCPp^V)J=eRcp<xk6{@ShQVz6tz<hOb&jBdSCFVWVA(Ljy@3GB%XpVC8CEH43;EYgQs}>BA?g<tD;Qj;DD9dq7gZ+"
    b"LV#@j2HcnS1#%lO$7-f`vN24LL{JZl;=cD-)zEHMqP@~WspX3^r!cQZ_$ePM`n3`Gl=Wpb$NVPvx99beZ-H773~OSpc&^IfMxaV$"
    b"vl@ut*e2t!Il_)pzto~8c~(v(P<cFprk8h!D+>`ZSHeY{VOqHihlYh_{zAp0oL7Wb)~M&@FO}d)=w$akP{(}KE1N7q(DH==b?5qw"
    b"!m`02udfY9nZRGNQ4HpkRz>%RLFETMU0AM#<Ip9j_u%Lx;6mhnZ+Z@G)&lGRw=T&sUZg$~VM_QqgJZh@e%D{*?z6B(wDUxQ{e~a)"
    b")`={!gfcCxC%&q-3!Ce5HP1G)0xz66nq0LBO`62+10Ih{unU1+-geJh?X8}V<8p-6WUNcD)RQtR*}-SL1@zYY;k=TnuVRZKpbS9u"
    b"rY08S&v>ZmAMOxYe<7ZRh*SXvqpRc^@=SOPc`EXbv#jK7p193@VK1ag`qIx<N8*%|g1!TXQD}t2yS-eO+hodBdlf@gmXd|B3RLG<"
    b"JNiaU;AiPyHIg<Uz6Uc9iBS}s<T!sVQreC?=_-GuhAB%@EgaYnx#Z%EQcdZ)DrQvzDGjiA2w9vWMm#8+8)IG1fj5`X#M7~uKv0Ts"
    b"ycM=Kq6Gc+Mw~$%McH;ZNC@>*Vu6*10lLn+N(g)@8g!b3JP>{GWWrYqyM1Je9iKO|OJM>&p{xns086WUY#50|`qXyhMS)ftyS-=?"
    b"UHueL(<T*!na9x$-(DGrHbCwIV~9UFBFMyHMNom90dh(J>N!wPaQO;vRP7=@BZ9Id;00``y6Q!(?)QQ$v|4eF4~A7wGCoHF73H<C"
    b"25dq*f$tCE?DMPvxZo)l^o&0Z^jAxLsS5&)nJgK<UoB^skHDD71#Q%oOlLyudQzl9c&>tFdu8!RJY|RZIP=U)t&28}Rwkrt%$v#U"
    b"CuT!Y)Wj+chi}6kSA^N^KdldW$#{I@{*2Tm%FKK!^EdCnmXa=5!+IhG7*EfcqK3-sdv6-4kELp4f{dl3#Km7e%mRj(z|wu?S8yQE"
    b"a*u|!z&)IUW29|X+d<|)tJKc~pt3}yo1s*Obl#tVT@Xru1r>!OEM$ZaYNg&)As#2Y57ZX?E_I_2qFMyF_eh#*tMGR^J|C~MG;Hjm"
    b"$!65{ywDrSUFDZ$$|U4Q7NP>Onu{Tn%8)kzaIe-S!^7A)?S4I8L0;|J_018=F<xh6k9YlGPXttU1(w&yhmhm-u?PGFTSy`KsG?gH"
    b"b+HcC@&O;z0hOT+1%}2M1`Mle(>E2IR1WI7#7HOj6uLJ8(nwOp)lB-aeGdpY+Fay3oX!_BZDV)G1TRQyu;187sKN!CX+W+3eWTXT"
    b"y--rs&U*zew|kB+Uns(?d6O^?RG)X2GQyPTf`5o#rgXBjOr!<a!AHOk;bH%7+&%uF>Sgvk(!BYtp%KicI~*vO*yf0YV!vpt=6?Sz"
    b"?|B&UUa!g-l`!bvF-%&xDhk)V+674{+|rdqsEe@outb5@0}_iv6Y{3-8n2;jXa!XlQ3D^t!D<;}mxLu<A{{JURz=Y*rRD;j#K4l5"
    b"3U)E6soj~h+xv1ZcNj)myi7EE29}-l1PTCdsaLsw?;E6O>fg!DHJb43{u(C<cbptah15C8<-Fl#M+cziUPbOO2N;j{#6tLPyruRr"
    b"sZ<nWu<XVmTdRDh4+M#oN??@dv=PwA>$!zM*sxLNX4AY_s!BFwXm$VY886Ul7Y$u2>!D|L9u)9h0pI@UX;cgYk3)BzOhd5nRTc&5"
    b"tAm%KzQa0*?C?tCDN6zxGpfvVNB2J|G)~CG^qKx2Oc-%JO*$$KNgd#mF@PIM-^AG;%f#(`9KIBD=rd&T2C88xf1Qv##j|SzG!hxQ"
    b"!pF=oH|;?EFwwg|Rp<d6kA^p=Ppg-KoL~lcliE#C5W<xDmAG|!7g0KQ!QPmo`-yu)-#Q4fi`wC7NDUas3k;d0*Vx1jje<5pE}gop"
    b"oH+0R0^hWmpb}4_z>Pn#?yN#%;0r%9xKa9{0HvL~II-5oePi+ubioHz7xl=|;S_Fm9TbcNszf5kpM=B>(i@yoPQ=5)6XXXbT7;;y"
    b")*CxfZ#$#V)rJrmY9+07i%`?WLezrIz|IIqKrK~tXlij}Q>fxr&^T(kbP)XYuuG_W;s~wNW#J3%4_YB%9pEHByw{Kj-9*<LQrR16"
    b"ev<BqA3H9fvLT02kRK(=`KSFN+6N-Uc>4K@;A(?!4`+tLzIwhTV>}_!_w<#*7j$2A-<&xOtGnWRjaucMN&3Qd>9_>*29?rTTn=RF"
    b"0XTL!T&>0i_p&rk<T}KH&>v_jM_%H%FXGh0A7*q-JXdD~+V;?RbFfeU6@+TTe{58IZvJz9=2V#O5e|*Cuz(UZ+c~wKHfhj!Jlx*~"
    b"E4x+%Y_M&Zd($fCl&%Q0Z}C_D&73jP$9FgHf2d6h$4??}29(-Or{c}uI#Tw&>4VdnaA<4*_=%_BDCjcVAP*lWeUxOnNauFlwxIew"
    b"wS1LABc%NgZj#p<jS+)C=L8<6^!|pE>nHSS4tYKC)P=3c<G_fk4PzH0FZF#b%p;E=uPQU7>twR4uWPGeuY>AZwY;kFc!Z3IKGM=?"
    b"3>$FF4vf+r8}~cG-MY!eqP2e>52;&&q;sw%zPGD!?9y{d=?yUhANb;^e^qBL<Fk6WYjS<o4U$Yh-1pIAiokdxX)nF}K8-(NM#s6n"
    b"jpU~M6@0+AMh|zzEBsX#M5<iA|9R=zicdyKN55EG-uG}s7No|1xgxBNyn12qkXaEW7yIeY1}p_Nk&zM++9gzxpFPkHP}1kCyeWMO"
    b"7eQ1H=sNBO$Ro{$*d_UrqeM6PrkGw^J(3K%m&Qu&jp)+u>OLD4jJN0k!-9a?Fi`Rv=mAL(z$c>+8G5qj)0#P$0!iJ^eAEgHT@c~{"
    b"b^lailo)SSYKs0z1d=0*Z;ict?}ARzP`M`RT0i|d?ic~}31|g)FATnQ(1N;)b^Xa&^XMFe*CfRjb{CpQ-o)N;M2d$r<YlT7#|A#x"
    b"N)sb|^~W!-SuivDYC~@AGjy6nyJ$^PgKsPtG=;qVExMx54ptB=9vz;Fxn1#yCO?Um*Y19i-p}!Yia`C9x((4(CiwhHQwmj0GhXEt"
    b"kahU0iNV#Y)9G$=R>#@be%Q1jBja|eaN<M^_uZs;;?gf#FZ<M{o!DpJ3h|Z4IPl*e*e{@+q7rj01;rv)TFp|OToLf8?OFKQ)at&j"
    b"(~H1vG5|j<WXfm_N=}6rPs>%EQU5caZ0N5IO+Nk|z2U!>?UnEUO6183INWl0AW~bd2lk^x{qRbyYVzV0Ki>l1w?7(e<ki{B9K`SI"
    b"r!9({DKj=m5O`VIneB?GbtlHM0TFpSy5xpVzkJVgAiNktL4Wu}G8y3`U#4*%8L2fpIpv{eY)F5{8S=#y_*2U#!C^82vX2gj_wO0T"
    b"EqiBHl|v34vcbPAI;pW*cHnRay`2TMNPkl@0)gkn2{GL+L^?rv=zp`x1bwN;2lqga^Bs1cJqn7C_jnZo>^cl@b!6eKCRAFJ2efz?"
    b"x119X?DEW2<jL{q76^^O0g<B6GXwch71XXLdg1#n>d{iwASfBWeM6UIkTqd#mMmW3dFPQ`D&s}j!33w`E?h^3(ISWs#2*a|Ki%2@"
    b"d^_?0P&pxCRxD@#>+tHl7qqT3=W6?=Zn#|MgL+GDN(d?Ul`!)5olqhTa1+Wqb2^30#eG5$6k9Bp8ifGcL|b?u4|;JoFThI6C$OU%"
    b"p2h>UCu+r^Q$INM?2|tI*(TSeRFze2N-R6a%J^ux1A4h01YtEQ$l^+Ar{ERGG{O}%Ouyo1cA;&_2^yq*Jako*b=8t-x-*@*b|3P_"
    b"Q@X);z5vt7eXx_`p*9SX23}@P5Ccq?^{np1Gwa*g`K%GkvIsS{*#}XEaA){6hp3;VO?BYRe{uylSk7C!)`nR+T%WqrhucsT?zxbw"
    b"8-~(WID$4tnSu7#SHEQ@1Rz@Mc(fk)Vfz0X=TM(&d35KNR9alwYSS&pjd}dyvcGuuP>&03(6s0d@3mh_y=9+ww%bSN{t;l$1HeMj"
    b"95-g|T}lXa?6%}_kDvM4$`gusZg_xB%%f_vI+xtbQey6q>x!<K3iTK2sA-jwJ86mkKJWHAMITAS$>kc)jk0rJ3k>q)936NeJkRbt"
    b"K}77ZP<z(GNtS??RSRdO(Ak2J!W~}r2ef)aP>5}EJC<j5ye#+V5#P%1uAd!jdg!a%4L<+Hhenr<dw)M)A0-&5f155<kS{24*O#~N"
    b"s>)mVRQ87Y2AkxsZob0hZ!3w5OR8JWGe)LA36L{);hDE(_CP^o_~4xQD(N2hYK;K-zl#63#Cs^m8`1;hT;X@?mUzn(e30+k(&>N?"
    b"Y<_}t8&7<GO`%GZ@+sWGgRerMKJi&zYWX?1`0+I!)oZ;O&5!ML_ElP%|7*zk4DThX_Z8c+u9#%gU7o#DY172NA!h$Gp>vYJM_#2$"
    b"zMCO?=}p)2b9YW7#kPE1E+%7LuDdH#73T=_y}kY{9OMHAZ7J|>ER9M2<?lZbUgF(aO741F`!4T6-2}9)_l1ci7|+mxS1+_QDoUQW"
    b"_T$Y*iY5M*@s>|-YFvj4aL&!x2C+uBLA=n-*y+#kN<M-Y3zN<ld5Uuz?`J0>NuoNUJxvnBw!Xi}`)vDgN2@Egsz_Nr&_LYpKqO8="
    b"5#E|6k$-JEUUY&iOF>gCie^A@`7KR<%DgR8Zl@mEPhwT4&3Piu1*u->=6|{i@0@=1E<EFQ-m?Kd9NEx+b}K$&AaI4rYFc`eTj1Gx"
    b";xjyQ`}Dfs-W&-Ad^<#GgR^HfloV3Q5^LF*6qZiig(5HI6k9}Z<8^LM)~ej>5C8LoZu0`s>1Q5FvB-;Eh~I^`e0oFfE77{@6Wrd@"
    b"?iVs&q5{`kc-yk+E%L-xz1U_4KKop<K!T}QMF!?hUUo_|K+6ipSs;d&eP@x^u{7?5^%uHzCyzS;e8y?Y@sh>oa9J{4`!kD9Eb?Nv"
    b"r6Y3PPiuW`K;AN~U1_dX<_Zf!S^k|rFZ8l$X$%Uy<zW&mu~P!b$7y`buL?9ST`bC4KRxn|tA+0@^6aHC@OXVXxK?yDnGcp>(fSb-"
    b"A1X0wKYugbCfT_hwX8l1?mH|=!^kua{VO^31Q(!I9D`esFYN4P6vokE)d+`hnq;^Vv<|VvHi>U6uut)YM5LxyXLQcZ-tfMeb;t7h"
    b"&yu%(4|W8WlJud0hrbs0y7RIO#*@hqeiGs<T*hPXvYK-|;-!cEIRoQdkc9#-<^E%#s;Rf7(_G9+hieM4#R&sa9<NqRv-T~x?yS}8"
    b"_1AOBF64OZGkIRtb=mXHvkYE6`I4zI&&_Lr*-S3Oi}KJ^BwqUvYaf|F1am8o=RWK%{@fb`{L?YU^W5gnJ>HJz&K7yO&O3@JtUUjX"
    b"QQ7j<#cQF!b4OB3JcG@z_dw)$o}c}jIbODyAha-;)i1xP5069KzgPXpVD21}%iOq(x27Ou>MY`Y&~fd1fD0^@s4Mbx<qUZf>KrNQ"
    b"+dt86kOI%HV_EM!o;^_H#qvBH5U;-$m5(m*jyb6;Ro?23=%ao$bs}!G#Ov8AbLaK<>Zh%99`F0EtE?&X*L%1W>*$o5{bufQaDLgj"
    b";P#Apyy5NcV!NC;ku>OQ=HbpVl>BUdVSeaZFOdSyIBH|5ojAl_WX3~tj>jP{Ug7Fq``r7b6b;i6rpzd_6nYo&uTNT#{_xi0X4#r>"
    b"?kR9iz;=8PI`?_f9G4;Exhz5~#>52+lyV2|$;-Y+>+@%I%2kLyV}Y{zI-%(?r@<{*6PAwZxl)(j{lI;ItKLX0Xlqb0cbSq9i+cS9"
    b"!EIU2n??JBDkg93odf^2g*lymaOOz3WDO@A)4e^JB^Okv*FH0JfiBH&p6AOJc~xC3{hjygT6p{nDBphv`+J^7%#wS>K#AAB;qZ2L"
    b"1=8b9UeZO6XL;*|eQ=nHwQx@%kNkyP(RbX}Yl*0H6$9TtE2l4ZZT^j9iL8J!(0o<eh{v07J7G;h&gJHVrGI5Sj#xO%@uZaJu^<ZG"
    b"+FiG`oT?WdD<!vbJjhGo9M5{Ri+axoJB*B-&0hyN0QVGf|1s~5$8!nYNl@8s-df%g82E~`etsy&%cajFIo{QPM1Nis)saFvb&u!$"
    b"`{FVl$xK>_7h~5TTmdWtBPrzkX7PhsZoNpbYfW)`IGca5mKJiNlW{>E@pxGl6;WxX2467Xg_uu}RgiyL;MGwjzy2f%iah6Ui^U-e"
    b"JYEO&e4Zy-ga%T5{RvKQE*+2u*Ol%s@M1cI_emaaQ{O9vwm1(K3#L{q>4{e(Osin+6CTw`uf96M)tf6uobcnt9On?D{@nPn`*LfF"
    b"`(<H!-cFw^@brAbdnKz5Yurxye-G;_kSq1F7<t@R<SDxJS)N$rrS#_FD_{P3%La7qCP|O<AUw4DfXsItsM}fO*^tQd#Pph?ZebNV"
    b"uGJNJV%qaMD|UEDpC@E=$7<fse`UIxKwMu@*q!;`Q2jIQ3l(w`l5ElbNa;M|@l>(nh9+JPN%2gd#C>h(+$cv3>8w0hUEV%eomr%G"
    b"-v(7rT>+{56M3qtYcPtN(^dRgHB>D+uueD-9o?X!cF*_2{apC~>d`-|Bf$}2zfOJp?jgTfiVE#j81i`32D+~idDoEFEl*W<53<rE"
    b"os2gf#n0X&AE+7K5X|v*@amxA>ZS8QO@F+cidFK^m>E>#V2Mg~&(-gYLNn0umn53H3hz&}`;F>zf5SG<@$yfE!!xGhX!rOp*IeJA"
    b"ii{WGc=bvAjuovCHY?(>v{+TvuaCmIuoTN|Z@=Dn-)KC<(|t`t;PEafH6sl*ly{wRWxD3ltPyjxbxPOR(e^~h)sObaIDWbgd1Fly"
    b"Tniqk0kN-IANf$Pi;`-Z8gZ&)7vmvq<G$LVFwVzEhmrTmG~;Eh&^+?=6t>Uf#Y67D!XvPQW4y{o{ua&q+DSw8?Vm%Q!GZRd#+Rz!"
    b"X`ia<R*a4NQsoBnRt8n&`b)1mVZ}AAP}g;0;^w4%Q<<z;aB%-)F038A?V!9;sEL}|WkCD)<OB5|>L|MR8ouh95#;gartu><AJ{%Y"
    b"m9IB;jYdN5bt~3&9duN=>c8nfP%|Du-UVE~JNWKV#VJwf;a;`28;s{x+5^Ui6Y2NQ$|hIU)10!JP$3^b(nV9oPDg!8MwP|J<##<9"
    b"!+ldDZua;;`R8M17^g_DucaILEb_=VIukEnCBwY&9Es}551pN37GagD;pj*s{~H(&4n?qi_o`3xHKX&<794xa-%vA+YF_sEMZSA1"
    b"=1#Hzs3zD54Y-CXztQ=7FaL+8VNrh;RZnRI9!IU-6V9=bM#vH~ILLUu=qG&5h+8udbI*498=|hqbNF*Z3QHpnXcKJmc;wA%r6mtG"
    b";}Uw7YZyH}LRwf1C{2jBLe<^63+53O=cCED`HTLkNRXxdPPNs%IvVPE9C@eY>6)<_<Z1T=w`@$W*A;jF$wT8MzuyE(TC5YNjP^kS"
    b"Nr5G&v&&}N&1M`w<Xx{n!F^GlimF4~LJRKSRv{1fgN5|><jI<T_FfJAnlH0{RB@k-5(uwm!6jUZ`IN{6;7*N0Vk`X%D7VK`$eSQ1"
    b"zy3vKDneSP730!y^oYY0<qNP*ncm*l@8yPX;(VEyqqw`mWHvSlRExq<7X9Fr%JFi@DWi>c>eKPyw3(VHKgoSjdDG<GvHokP_V^F5"
    b"Xe#$KtP{Iuy#39~r$HO)6jw<2couvciJFd4r3Z%vw86jO@th;b+ZUWMQ${)VS6R@J*XPtl{S6)ukY}@6k?v$|g7H!~AG<A|49bd-"
    b"8D5Ns4+KDabiC|%%;Wu}$4*V|i=m!>H7Kfok52}~#^!!?J{s!rcoZt|M;|LS#GHN{MJ){XOaGRD<UjgT%EyD6x@1q-O6ru8I=wID"
    b"8psRiuOLrPjajZ94fQ(81!iC)FWcvKv$E63%P?N`*tsYuH<K^Z#jgalf}gaOU0+OPb3AMx1dKJvGg7YY>grnjpqE1SOJ4iVxQ+VC"
    b"&OFbr3`DuDbMX@TX`+2MFTxhFqyJP2na^BI6?uHu(KX7VVTN2M#;RQ7;Kmko@z0Q#cD{`>vl)oTa~@S%RNoe#-mwo7Ck<X9(Ism+"
    b"Wh2iUKVBlNzt&dQje+X%poEI|u=Y9qAL;zJA=f^KlaVLLc6TQvS|{2iNGzF&IC6O&8WC(h95jYnA-S4$OtRr|zsH-f<4pJTdAw3n"
    b"0N)e7X6Td-?~vq3MSNL(Amok5aJ^jRa=crjlPd7oKaW=^2=b`MBeO!^iKlpn-`D-QN4g@B&@waD)l&oGUi*#*fX#=4UoxOEd8K>`"
    b"T$sn_E0qQqfEJFN&$X|<Pd87l`cntxs2p23BdylMxpd9=(H?MH#=ZHV9?w8t&%`Bbn>z^Nylad9<abj#(No@a;5?6NXmRho_|$G*"
    b"Zmb^>Dm=|}x|an5UnK6pc<Lubp6NpBl8J_D&uDH)kXJZ)A?F5pkH=|zJJ~ySVaHq2S0+XVpD6~I8|)T)zQ5W(=XkWa!HS{b`(92T"
    b"xuq=eERW~z<aVrR5tWV$T7>&!V^aUKC7xr8?(5$C8j)`ctiP@io3<Z$J~UsKS7j7;I?v-jUFGp2>z-UlcVhP=0pB0%-SH@2sIrlL"
    b"$x_@F<e@wb2N;jKY(Xom$~vP^<)Y%gUEsO6{!GP%id~auAGhH~L{(PP_FPH!Tv6V}@esBTH^Y>{tt2;;Man+l`jfHjjCadQIi<|!"
    b"i_<u~ljnWyr<3PI3wf<HB=MhL9#E~v+?&`w<nbZn71llrTfgE$!O9gY#6tFOTXc3HFO)s)oR6Pf-OPWwu7-+Ivh;MQP(s4Hiumci"
    b"7)m%p>_Of<+DDx0X4=I0m}l<uxA;Q28yuSR8CMTwf8;wJuUgf3(uAWrFIlp;nDRW_SZBvQ-dGQGD>r%etKR;zqMP#GkeMsgigApP"
    b"$4g~1a6DYcD;*{@=)4RfozF)sV;k`EpK3AuYC{h}P+^^A>AW32>n>)!oUD3->x_9-JYvpe9yO0F)sH9E9f<wXmNx?5E<Hiq-bHVM"
    b"=X-Jaxo5N#@~%P*=hqV5X`1IXF3h-N`meQy1$Tz=Xv{sqV^6YYOwR8+Fm$PH)kY~srKkDZOW>T*VmK=XKNMV};8aaxzszPnmm7Y_"
    b"I98lJ9GVju>_GO%p;n)7|D>Dl*)&2xTC*(Pnk|kW@AG&7!B-R`=Gv(1IiJ(LTX}B36~q;l^5W`I+wx_w0om_d*a0WvA$#)VizBe<"
    b"{ZB$mRbyDNb~W;FdLSwU6`U$Np}0;+%Uwzsvey^dXA^gk%izdluNj;&m3YK%3coaRbnpxLVk_R|S~k_C`%);lW+EaDD){1BlRxE-"
    b"6?@rgvvVX|I{0KF4?E!KA+BN*>I1!*>X}xZjOVM-Ttp&{{cMiM9I-(jU)WoaH&o=koa1>zeJjVSi0S$X<+55;UOv`J%k-rvb+%L6"
    b"<%uRScdIJMPQI-7@Rz=1VUROU{<;AU&BAr2t2-f}V<%SkB_J@S@72rre4hJ8_DH(!DC~>khjIT9KVdwBb-J!e>@A2iI<uI6GFdGg"
    b"Y()ngi~THAGYL<OovPNo6VriQWDuGa?$E?O31@i<H28$s_*6`{&%|ztJ(nzBvU%Ew)0xBFpG;d!h3426F*$Y$!vDN>tpQJOe=nln"
    b"Rx}JhKZf>Oj5U*4_^b%pS|*-)is!U7dhrYvdDwvo-`n(n?vPHXubq&s<~w-p;PI~hwT0t{FRar1+032i_O6>)#dv4J;-!hciy(l;"
    b"&+7ZF+t0Zj0^`^fhknjVZ(&91RiAO&>3^MB++1N5Q+)=-@n>Km+t;3e)u-GJGjLl0w?$CK@vH6jGAI4_46OQ@z4^JKn<aFic&6*|"
    b"98)wdN#!=7CX_3^tqJ?KbMASWjN>3@+d?k<9N3AA$YLfIitTeR7I=%u!wyspY;x1eza3{WlgG}&rQ2)BjQU|*WOc%JFYupWpJpks"
    b"i-nqUMO+H^ffnE~wieGnZn_cW*QcJ%#48tcIClHZhBokczc_ub%d_H7mZ4^EFWgovS71x)SO<=$I^FOWt_5M%x}Ws--EmXmIP!3i"
    b"?aB?Vz$C>d@nFb12VGdI6P5pWO<LE=u7bVMHWeSf5`|g&vADT*diM5vOh6dVpV;uO(1eY88pQ3n=arS2T#`iC%J1?gk!Nnm$h)<X"
    b"@hHsLR?7OWct?#b0NgL#^jd7FSG0oPdB^>r(c8=Qnf&(Pi%<Mz44yb;ODXes+3n^0aON(simrjO6fI-roj9~o@aK}y9VxuH%&L|+"
    b"5$>2ewdbJ&04IZT>INsW>d?I?H^s%-8k{q}<YVld6-ZI~49;tk*SG_=XsvEyNeAZL?Avr~#=X{)FUd9Sn%s8v#OMDnc0jDkDF^sP"
    b")Gj6x%Zf~}i+|~*J)SPx?nBPe(|d+I!=dmm!EF!nfBG#QI>}%EPSuO|Lbt@+ow>umv#3h5;%;;K$j#i!egD7nUQlA2tPRKEPea$p"
    b"Qf&hG6CWSoOUnnKqD2(K{zvzWEzJG%B(B^^b9*k?2yQl3*jpstpc&6BD?u3%dmCSE3NLeR9XY)rz|ED9`=8L)w(z5MAQ&vnUS4WW"
    b"56)piUAptS<mdHAB3o_VQgd<n1y4U8komy&GiMC7MRfhJ#Y^`3#BEhOTYN<ug4|r<t+3GQU>23U%+nosAmHa$35}-?*s?h0hg`X_"
    b"B_3o`ZnUB(#z^CmW079~j@`N_S{RIHz78B8*mYnqXe=0t4E>Qic*&TZywA9s-<|sv6@0!XR_%7_J7(K=qrLhZKN*~`K=ebTN>AR#"
    b"Yf9P1veKuqW$l{~Tl`uWh;bXww~?29;^O42u(I_7qr!JiEBf9&p&zpKgG&n{w9JwEw3z18r-5JY3pF)K*dGmUO@$`?fyocdlk_;;"
    b"Hp0rtRb$yMr7Yt$u~46{eugI=xF2}FXU7Ud-_j&{;nB-y%tA}-?mSfT^{})o=z{I~yCm`8Mnc`d<po2((G)VNmQ<GU`2XVb?y=v6"
    b"S9O6z-8=3Fu4<Be@i3up1t!1zrhahGmNQyC1cYTgFL%^kd8_}mg-;t?VmVK|#))P)C`2k*l^_Ak2<(KwvIapD938(qkGl?X<)m<1"
    b"R5L%!Jqxo!=u8~aV@@r%W)^nR+jvP>AHO?~yusQBxAmBpxLdNFx&VhK(%0*r<kn7d8@c7{kLgwP?mU=dj|YEybn`VZI^Nsg&9jJ}"
    b"&~*?e{m<RbTSY_gTX@G>@c%a7&U*#o$J|ZG>vD~<J}OS~2Df~@;Bu(@|Kmx@?GxO5&%xxyhHk#2>sY7w>Is;HIJbPgfVh0Q+|FCy"
    b"!W%MoJ1^v~&OEaLdG98wR>yuJe^A$O+j<86M)J4uLOjHOVc)^a(7DTyZ0SEgTC=*Ri>nWZXs&&^l4~fjwBN?_Cd!1ohcmZIxA(W0"
    b"7VNSH@24U0bQkd9pHL|9Jnbp<TY3E1cs^Y2k~>u7b>NbSA03E*;xk8JMI~+=*YZ63jv$jed8gyy{$f3<9Iq)eB8BWf+d5oj9unyn"
    b"hL83?e_E9b^?SV$fxK5+DDe0~HAn-<gjVo*=LXW{;XxhkN_^0gB7LH!ojiY<c=cjX!C1JB2cO~L-&gBi+!xd0ay$yjU|a+HKKlIQ"
    b"<U&;LdWcGLPTkFY<=uF;SC9rQ@Up7r&iKrnH;D4dAg;;8N?sdVEfHBi1f(|SWa_7P@&b9DmCD7!0J$eOG*-&<WTQCR16QBMNlLEd"
    b"``YitrKfMAK5s`2&F9w3UHhBUF;GEyzE~>RlMABFybBK+#0roTrauk>{@$1CuOXiPt-N341`GIbZYjiJK+A;%DKzL0zme`*mF-H5"
    b"CgA~1fU1!^&nT`J@shiJ8PEBHJTDh^=Q?X(ySI{3IOM^-#_KGr$rHNv8Z9j(KZB5!yTYByweNgviFfPM?Rj3_yPwq)b-6=1TT=BW"
    b"Bc~5`bN)~udI|`;Oq1g|T#?r<nk?fHm*-iovW#b<cCY7Rmx!D7lQttZ@E4ze8<NC|z)Bj>68ZH~u@oC5I>AHB`a3z6Uu=c;<&v*3"
    b"-XW4PLj%E&0&a*CmB7l(czrU@vzPHKwPP7i&$o}}k1y<dB391ivz1I{@sSa=+!Vj><9k}-&#L5Hj@Li1jCTu`^VIta{mm)(<Dqw@"
    b"0<X2ys-$Wul-_q@)Aw7`+x%oyzRk+a^U9X-@&QsVl;jP82XhZhiseT%VG}Expz<d+mH&d4Px;#9+pNqy?{}B+^4Vrw5OVkF_4rVp"
    b"_bI!uitY1(N??;T1aWdN{7-qqHF;j{=)}>#?B-3#IX*5`)UxZL<p%#obP%2;5&ogutjs*GWEpRS6y}#nmPK33>2WyQ^J4rdd<-I#"
    b"S2bR@{oDa1!q@&!dAxUr2>(Q?8qCPwLv?}o>Kl+GdadSbRrON+X+Lb}IJ{iL#<#HhNXUD68SkT)y?_lDPT!1x&u-{z%13y)!+lgG"
    b"y6=<Jn9^6tcgo=d(1_MQOKcL2=Ph}<19^0L`~D=I@9(aI_-!RK`BPqn2@RqAN|e~C5i(sllrZb+ts_+6stY`Pi$-^ZS$|no0OSQ2"
    b"kN5JyyHxbt+-@t)^BfHXRS2%M<GMLt`I{ir^|em43u1M7`>v70DrKTq8=0ySZ-q<5YIQ)-H*D+5xPQz;`{3@lOCR=lg>c6hs{$&3"
    b"AeY+-{nljVTs!0GGV)$+9~yZHdAI_!k?F(YtpxJA1{Hl%6nW>7H^q3~%=rodh%xsDg%%Lf<t>Skp{?KxLuG~xg20c>T&jk3L2svq"
    b"RIepkMhS262}KXt4)5+D@VHBK*SpONkEfO*^}>pYn*WGirRxW9ms7(p5*-9GGIgZ7y6s6ey;<$0*G5DuP{NNiL==7f*tExMc<EKj"
    b"#t&O~NiVJi8deO#jmV5Q35v;uT@nUC9J`*H-H>tE^ky|yi5hw2lWA<<`WZLFc+>7%$P2Or;#4ahD4mHb1{$R=x4wBw*I{f{k=_P4"
    b"A^WP|xim0%;H<F;Wu^AXR3obSCBALlquzY<ySsSOJ^CDuUoZ@1se%EFkIH+OtBiS9tQ<M~RzxTEmtwHhOV1vwafb#ESmq(usnKjF"
    b"$E$t~c?V+18z}JDor!q3c!*`6g2<7v%?*_!&-0tBT`M%pi4v%S_{npPzDRJICE^pc#)UDq{`gV1R?%yn0~zGO{9E134;zHgvf;~8"
    b"64|QQQ|mvr#Qv)Ogz^JUB(PH8M|L;*s=B8nTv5pTXq55D$aEBWqYXUc9jWSJ<EQh@<N2HgUJ+Vy=Ctb!RQ&nu8-|ijC}C21LJJGL"
    b"?Mpx+)FFF3H+#}+-=!(!ZFeuF-8J_CJDhas(-WCu>@M;Qy8R!t)Xgi;?U{Tt9*Q;9C7PpsMpzK%%17vEs@!dLukrYNY-947e~HaU"
    b"Y+F~K`+7O)9%%rV95;%wtV~HT(tVG@*7++*)SI=kK08+CY_3aqybEc@d)XZp>qn+u5^X3G7a1>A&3GZ?O~+mSl*y_2WD|_{0>Gp2"
    b"li#SxJ*dikW8mUTWn+oDh$M*iU;^HJZ^BKx<D0Za%SE0d+6}Dk)lehv#$#l@y2o(E*RJo4FLjs2qdi*o&-#V0?}>AKT0b;9wu%EC"
    b"Zt(4c3AL(w+U-kGUYk2RD!Mc)jx^x-1sU(^HkhpLHrxP#RcO&v(VT|kZLoj&Q~y2kw1IZN(eP0!z)Q4R7CUC_U~Fs}2OW6LDPxBv"
    b"4sT9k`(mCSqnAv(*uFq62&$k1USt0&AFT41?;ir;apUp65XZN5C1i2KJ0n3HMAwXA`yBBl@dmN^#<SOP{9>mvuJu#$$#vIjAIsUv"
    b"QvEY6f!X3vW+fgj5A~p!+&QR1!^-q9$YTG(C-;ik?XDH0L~}b9v3+*QoQ*sj_H@>DNY?Qh&u;kw&GRH?yFR`U7NDWSLRE-wHyc=Z"
    b"SiAU%lUz&e2KSsFN;KC?77TnhJ|9MHPM7q}Z|jY_u!H1pGkaQxcbdC%5%=<jcAeA-{43^j--`(0b}{QD)~4<0Bkz?mUe@z3uI-+W"
    b"GAGEqcUyaU8;&2{nbBk~M_BH(ET>WuLyfmnQWvk=0?&OXQ5&yi-3#@-gvyC%@>>3#Ar@K6o@n;GhO#rPzg$OA78I&jZ@1G|gm{MI"
    b"AD$kN`Decy7H@3f8PD8S?oMZr=eV&PFT0G_J({BUXq4x=8(Va9VnKkY0e+!nBZ&TaK;C8vgch%TX6hYx`uGTIpI3d$YoDIyDLvO+"
    b"#><~>)TWlsNaG-X*z%m_^RrSE&u+%=*o8bZWGmCDSB+-T^NIYjy>^DV?L7b7TkoEnX{hqFtSDc+d!4(FKug34xvb@D+II!m(-bE$"
    b"@vj52m)zA+X53eer$o)or)ACYev(Vm+ECStdK*Z5%N;z?SKs>juCEytph;@H)QxrG`tv+@t*$$5)De$2<K+A%dZA;lO<EzBUwLPK"
    b"ruD!@>obOgmOJQbJnmDY>u?xd=E=#p&Q#M{vEH3t^gNL7x<*Q`bKUDHcd_TS8RWsrJMLODv%#*XW;y=;OT2Y3?yCp{sMkK03KXZs"
    b"&(|*%EZ0+d-T~IrbICwn{^%`G?DF;@YVGV)69EIB+BtnXEFKG#vi{<xy=cUaxHJ59E!FF=((%(Nmtc=$^V{5-F?X8z(`e6~_tV|;"
    b"NqgrH!>!$y0d^haJInS5WaOo6<eAFcyEE{=>#290BMS~bExpLwx_xq+TaLVHik%1+^5GQEGtpH2o*ajLK;%EX=C6?Yw#oSXdd|jN"
    b"luOF+y0|d^#w8S6dW<DSjk@mSk8nh^iaT>(;ovR)b%L2{#9x114kJ&3cAgE6%Py=m8Wm=6s<G#K&GdaN>_xA27p^y5f60AkjH!lE"
    b"L0BHj@A0<vuAEwv=rWZ9Cv-ae-_GEI=DifSOmNN_rO$_0CC+2>y{yqVzgZ`Vf2(1CrDvAwvYx%FwKlq|r?w;mxIv_iwDd;A<LRsh"
    b"JM_MWdwd=LZf;K5<g)qgW&ZAI7JQJtbNPjAP26v-Hfoz9;BR=|$VmU~OdR)LoJn^vMq|i>TcnWcjOKYb)9wr#VM_19Gm^D|*xX8S"
    b"YVcsA2#QL>GH-c4W8)F#xi1!YX3tFV`M|Bf&3<ra`%<>vVK@(!cZ>(bN&R580)Ccshc}rU%C%&c-R@9<!JZkT$ir7o?Vas&ZC%kF"
    b"Sve0YeJeruKmmf5n9Lj4nb{xN@^g(6uDQ_Nc=#=5>~1{GJ~VV*f}0?I_<;*mDXPdK8z!SNr%D_#*OZ%-33cXSjpq_yG&6Uw(RAnX"
    b"bM0MztvL}oU%KPwh|+g{H&nWj2=bWToHO;|5672zG>zr10vi7;59D}a<}n@3obi!T`Xt%!8UcZ0`vK*0-D$FxY(qD`?8=XO_USu#"
    b"X#av_^6g?Ds6O5Fliu{6rZY^x!Rd|X?{8JySn_BtyXS_DJ#5~&Ts+={z|VkB+>pIq{uWhh&LR&7=T<!Oh{p@Pw`3d6=*xJHIer&j"
    b"nb|4mFXAS@_1N5fjoH^Bj?W~|&Z9`o&eiR<m!)D`=1_AE>v!-_{Y(a52n1x7gMaJRg$&Pb$LJ5_MxOBb>m186+4V2u&6jJR;aOUw"
    b"IxNXrj0U#egn#cpuSUVE!;BjrDbIawS<XAXaT#wSt>5AB?8WtTxcht{-A6-@MYN5L>Gto*GVye49Zlhs7m&i-pH}W%q#*9S>o^Ae"
    b"Y`QxgR?1xTPt$57T-7&NogM*EKJW43u;EmyaIK`^mDN(q+LDCNX5(W5j7uiasts4!j~nT0Ahr#b5YJipfa<lzS;{fF5MG{7GP=B4"
    b"ePO;>eUyaB2j~M4ecGT8!E>eLWi}CT?*o9(GI{HJfhefp$F)89YkwW{qA>rU(3_>cy?5fAN&O*{`!~zIH-0l!|Myjb3}L}6VZLY("
    b"jd&{MY;#yuBr|2#PrCY5X!51ZoZI=51Ch^+pL6=j7s`#up3z8!ulabQQj+PHslP;F%P&5uD<NVuCxJtKsEsML?ZApXKo#1Q9I<q$"
    b"{!Fe&`oFxO#v@Ol6)f1_OAt$@!xTzb#1;Vq#GuSdzjIG`#ZrME$!*}3s7#cmuK?8C$+O_EI@SH1BaCN#FOg<E0wpn)6SE6-epP1o"
    b"95|-JSA<!aB2LSIKMax*+~9~b`gvB$*J67Bab_&Voh2QeD(M;?Jq&{0ZpK?jD9$uft|O?54EWT7@>C9+f?NfVVCi{()SD6(G7==M"
    b"l9$?6jIkSOe8*+|^HwK>HJ{gygt}&guB8TxOo&ue>MgKx!pm5r5r@|0m-3C2#N34OC<sr#h>E&6x0ZU>_QJgBUeVYt9M&p`KD!Z@"
    b"!EV|fAOUhS;#FXJMSHf;z7Cy59c0&zxi<2c-)e*7+a>sW&U<1dgUa0{OIQeKabWEupx;kmdnVn6L$9v9*Q`15<O92?bwAF6CawJQ"
    b"+Z^@t!4C(qGk=0JMGo@ak*`1$DmB!c<+obsLA4X+nH>^YNn<U<<9Vfn^yn2z$v47bP3oy|E9sIfdFnp*tOkjI0IQF)By7wl8y@g-"
    b"qJ`-bQ6S$%9fL&6^_W23&(NH^e3!n>2Ab)>_Cav##B#4Y4rDYz=t{`()BsD_Bd}s1fjE7li4Q4M04_}W>oW9L85$mDbv<@#n{Gnd"
    b"Q9#kfkn7$q=i)B{-@fuJRnON&gTTt4uzW=E!zh&x3Ose&n^992;l<s-;c&cFK<gS8^FjQ=n$V`P<Hai)OD+66l=nx^>FUHS=%c#?"
    b"-%*xQ%BYC=h}jC7Yx@!=uBwOSx?wdA0_nHY(m4%Ra;yTMiM6iz88s9|L^TSFv<Z4f5RC=O%H7?YfW9^r$ilUjqhzB1wP%x35Y-{J"
    b"leXC`xn&t>54EL=+fHEg*@!og_&lj-`S8?)zKoz4w6y|MVZ-~B$k^x7T3Q2}u0X^>-gA+IS8%CkY8j8f(Fr*Qx8=iPaY?)pfcxb("
    b"=8W&_*`i$Lh6q*t2R{7k<}DgY>&-xZ40W}7=?!@&Dj2{=5A;^B>fe0&fbCsq49!|3Q`k0#&JuHdcs*MQ5&81bmS|#YXsw~aq4%q9"
    b"#B0)Ny%to1l3J>K6E*<cBzEn!#x~HkbpPz;=3~W_&}3_2(bT;S@Ox)ju`1{yE$V?@DsjwmiwDfbG+DsWVE0QU<zxVKjui>{pmQ&4"
    b"-_dmVjke-V?}GS5>Yq@({Dl7j5yA%lasZ#yHq@8mn};Ft5~=(@9t2ebO_BI-2GGKr<v{2=(M8cFNof3Q3GXUWOpuQD=E8f9Q4u1#"
    b"UO9@2Q&_MjOQ1(T&HYguB&!V)Jpo~CpT?dsiDT=Qe;0Y+L(2&pHOMd0{B6fJ+>fUFvbpP)6$z*ueaTC{VX&lfr@3Za)Vnoub~i~M"
    b"@^};^l@&pJ{1h?%Q1Cs-T+fHk11|N{rJ>iJI@@Mn#NQw|H5+p~3@%<ii#+|Xu`)=Z?|4`x`Y4ol;XZpPlF}(?f^zC56zD9K>8>F1"
    b"&?t$UYsZ1V?w*~rqHwe8=j2&tq@yJ`)Hi25{73)Kf-+%UD~EQqf3i~ISau2Kkh_-5q5vYqSMdS<s1^SK9`7a(>csHDESmAS+f_GM"
    b"NpO#cK}cn%W7bi(e<G~IAL+c(XPMqv`PQ^7{u#*NXI{R88gsbRi>H{8ljLWm4c&)3uysDDxkMo}&CG<W!n+rk7CF5s_CNT=2^2|@"
    b"kRjZso8EmjQcC6B_z>%gF&hYIJ3VuWT*kFcQax|dXpnRmVc1<)j>=?g$VKDmQz2$y-&5{KZkD*#JkCT+mt%SY7a<=(nZ2grsheOZ"
    b"I<LyP#A%iAYz^`v->k|YZxb%6FW0Sk3gD<$!*v{DeI}Hr+*ijOv_GFovzh|I*r0@)F&Y^WvgX<Fpln6hQ{$BtU3q@x<)h+e*!vo-"
    b"G_J=t2=IO`+Zc=ga%X-9sjLnwm|6Y*RrWs6QC#Vr=y$71T`g$TEnrLmO?L?hFph&8a7@d{>XOaD<g8=J?(A8T-Des@!1LBIjoGo="
    b"MpjiL*<uoGk?~}s$q*!uXP^DfCNVRU9m}!DDj@~QX9Q9*a}qqZQORNu^NdjoVbnscy6^jLbxY#UOm;PAEFo3@>i+re_wRmxTs7fV"
    b"+AD2o!Vks;$U?x+WVYciY)iVa%X;Di9i^WH<tf(8WIZj7xfS0F_0=mrma(F^G$SHi_+O<29t_kRhE138mIrOMhb-UCdmtrO2bPXO"
    b"A3o~5u*-TTs!+F3WV6GU7gH{7{u%xCSXhQK_BsV0$RhoCVi>Kret~z$W$i5|EU;@Kbhu_SXtL>-ha!kqp8d}bxPkkqVj`43KN6ca"
    b"SA#8-#jPI)Jd$rTqQz3e>D*3qBVLvTxmh{DKaBDwn_?%LZDxg(fN84-Up&*0iY4T{>QW;@+TP#qBfPjV%y8L0K|agg`28Gl0U^l="
    b"?;LAH%l9mAP=~uO<EacDM<T6K0*QX<(2KoRQqooMaZ$jBG5N9I>j_LE-U4<UHI^uzOG*WUh+DwBm-jQA`ovkjM;#yPrMkaJzsbDf"
    b"PsGd3z)=`J4UMpQ)Nb%CJ_2QO`T*g9VM3U>x_TW~fub|2^Fk>NqFES&2(2G)Rrx5s=>>Qc&qGj|6OC2kazip;d<KKv_AxI;DO(-D"
    b"g~QX5t!0;WD#hvl9Dn_vJiI2m1-0V^oS)yoE&0=28$dU8af`i{SHeo245hYC<@74!x~Aloqj<|z=0!US63@Mew}l<KF79-v$JY-_"
    b"QF!$6_f<4p@Ni|R@MM2hk>PAIQFFvE8tSgA@XIAnp!WG_bwGiYI&_7o#`0n+58Ed2JdcpTL(MvOme=~mtK$$7wW1rc8mvY<mPEJ?"
    b"JWYSUB-yDv!%(-YR?2+34~#Itf!0w_WL1;{@NAE$y$$hHfp@KfCn69R(j<Q=j2m-8>PY!lpBsEX{ZyCs<Wu%DR84TFb^3mB-(6~H"
    b"G1N|%E~D<>Enbjji}MH?5o$YkH*x-r2l=bE-%AJblZ)~-Du#~w%S$Vs0-TzWCA>d8G9fC+NTt+%HFPode^E{<_wb@wmG_{k&)p3z"
    b"?XSE)+-L_gh5PtqH8OWuLWv!EX;&C3=aDjocss1Q6E>2N<d+*_pkAyvFXAo)-WLh-Q3z>X+0HZVywmo3zDY)2aq9hC1(xq8dKgYn"
    b"V-p7cj#%@)v6K1}$r7u|2Qjtxkx!^-j5*ZOp8LrcW_C57vIwu&M2_?B5RN@mqo91H?DJMI)Hsa#@Cf)%{5R@P0WhIAmm#NlLjUDo"
    b"p7K%C$j3-j=FA~9*3GHs`VsHA2(RA92l%_A9%1<n^^EmkEvkt~jXqx$z;U+G-h*puPpo<phrhZDe%W%WB!Jr5HVXXAH6c5lw1Q?%"
    b";!|Skm&N%@Zzpv$_Ebnc<5bn^vERdo%czR&2}8Cw;}3Sn(@)~-Rv(2D3o`lp7C@zNSqu<+wteO$#;3-}U>zg8E48(Rr(X}LgASEo"
    b"6+u>{)2~g6!mqd-TWT|-oy<3J%%AF1e0|Xq0`FSmL<>j3c1bEEatsUWt*#ms6p&8=+wGLe$Qp1+hHB_#8gultO7;7F_#Y|2*fB_*"
    b"Qo=n#v66Xr-z2ImikTxdA!j<=vr-e`Jnk;lWnG?Jey}2&^q~ghGb*SuR83A*sNyr#<OowlWXe!VC%s$Z#FeH``M4F}pZME3^;5@_"
    b"{tl8W4}OvqB}JKpgJ=fbM|HeypHEakr>+Haw4fnXQ9#<lLjWyPUf8K*HsO*TtKxa!?~mYFZX?qQk3`8RKLU!^s@cYw`6zxq19m6c"
    b"ky5e*d1`_Rnkt2ay1rnxaP5aYbWF?hFtiEJ-Bdl2HEKWV!NzQ{AgE1EcN}U<q|nwfp)GdBjhR*={^^P;CW)i%z1&s2NU<tT`hGaY"
    b"ypU`05yX?%CxLY^MR-(mgra+e;29i6t}0EtZsmnRZtuGWl2Y&inIgW4EXb4WN5x91DR@DLZz7%uhR7w9n>$y0@aeQ|;KSuIQKgf6"
    b"XEND@<H3fMp5S9=oZklc#^mi?38?Q-(f8FcV-YEZk}=bH?v(T~Kub4CMcVn4vdMsFm4IZ4KEZ4z@^`jlq4wqmh`~?vnfkB6LcG;("
    b"dZ{w#zH4Rf(8OT2{iFD@H`Qmw0T%JB!rkJO<<)Lc-E|YzpWC-}iMaVUs&h-PBGWG5Ep`e^=!ldFn%Q6fSd{6%xp3`Gcr1GB3yqn2"
    b"w{{@{&MDOCLG+sZZ^n~nd2TJZL;c*SSFuDEs50-o&9yDvyqY8b241ibqL&cX&5})Hw|R<g!ta?0+hljZv%TwMx9IX!hsXVJn{RRU"
    b"*YK=Mh}-eXydXe=^31P9`|VvyKv^Iahg3FaR(p`!CN5&esl*=lD$C#iUo5+2c=hB>5|ok#*^y`AMXg&WE(TrLV&;)H_fBS!?4Gw6"
    b"D=QvX!n<!~qZXXI9nW)7i=joujF*Y3%QiEnZQI$@l7*SdYtq^Do$(SL$%s-#5Uh*SP>N?<xD4{FEyVgQh`{9H8T#}+oxKBIF{(2w"
    b"ChX#W&vl9Tq7@b?_x0D3H*e1jJMh)Qo$$26oo^=Stz+U=`g^0!jz+~b*}2Q+`Px}I32=LPZZSOfx>GpaGH(v>?Cz@~uO@c_|8}O2"
    b"Th+YD<e(+STF@lDnO)tEC;3JiX1GNF)M}E-j*M0S&jz!~-kZ*E$-jwr+t=ma#1FckES9?x{o?+2@M?bp|6|=$mn+!ze}WhJjpL*F"
    b"ZrCgEiWRq|-;5V56zDEKZQkPe1=uO#fs5T#{w=&)JLPCI&nI$CIA8X>ka^nw=6;ZWG7jG^#z?2knfxjK-WQ2uzy^ejip@l(-||(}"
    b">wo3s)4!MFO;dJ-$OLw0^19riPSd^1(nk4Iboa$g9d=0KH{<z!6Tie`K>ek8C~?4+OsX_y!#L$U;uPiG7uQ>MK{m|bDYv*33wP@H"
    b"5nmNUg(a(gqux*MAMqr42r2)>i*r3?Il>gW3Gb$h?c!-}aiSM}2}G3+xL(r$%FV+M$MgBL+tSVL#2#(MzaSpYH?J78@hssPn-K$S"
    b"z&CRvkUQkYf@kuN2A|7wTW@r@8FV4W;``K3-+OKnRTGbs&%&c=NSg|HQVp?W%UaNvHCbW^b;3iAwIN|tn<J38q3|p(5Fo1DW6yp*"
    b";E-#?ot<7J@MK;{Zjz?=a>QFlcPIb#UwzvgGIcq8Vc)zT!J;c#{#!mdIzpyrZlI4Ypa0Ihvp%Ht%FSo@bH|8Isoc6U3onTKv(YWo"
    b"L}imV9f*IH&(~`9ozE|`&OY0jH5Oe*yeB=p<pOU!3y+Q#u0+{Y7;m5566$>F*YbnG^6MX<s)z=MZBCC*xTV>T&B7IMNfzqbI{%8p"
    b"RL<R5`#~#n)4!Hq?JiF=+OV@f%dL&h^nAl)n~oN;E<n8mcei`jeJ<T=fm{1)#~1GI9Cu*nP~NmRI&pEKrI3=rKprn9DyV-0YYEQ{"
    b"2u<cKa38-JZ(4yoyD@wLe#-&#4cE*jocN5=5=xffR$edS-7D}Ek-hg8yK+8z^VRokVHZ<c!R+RV{=2i`8N7dQsC?KhjPGrkx0W3>"
    b"ez9j@=&s#$Bhh^OtygETmq?+KA5Wjx)fn&~Z_g##!ZZA(+zRp$*Dc^RdfaV}7~d87{SQ784HmZ2zAX5%?5BLnP4Jd%Dta`RmV6T-"
    b"-o)R|McStMsgIq9;0I>mrbd0c5H>N~?XBPO_kWg~YT>4B^5^o$O!uc9JedrJt5YwZmSPf2g?MnXB^S+UGxOD~C`nn{Pw{?#2dntZ"
    b"`nAIGcVg7;XDn(nUJps7=d{e7nr2eOpT#}McbU-}i`=qvGwa9JSqb984h0dbZ^81n8+?vjw#LJ&>^uqcoR#Ce+YQS(d^_2NjO@gh"
    b"4=CU}Vbnc%Wzh}a&ryvt6eDCwDjSBmqdY=Byas9YTQEngU$t4lbB;lPkv>#V1ALMZC>Sr6L7nyzSAuS1zHGMqs2umyM+?-Gvzx`;"
    b"$U@~gJgA`y>+Bg;t{$b<9w3_bsLV}V4s!KMSyAaAyaN=pA`Xb!4?YoRGd@0r<2wllG)P(CPz-^$<T|wj6=Fxj@dYi!OYn#P?=t#>"
    b"-=M}L0M89vqD0Ou%RxQ{k#=6p7j|>0F%*@S3}puSV(Duy;Rzu|cyqGuhJ4~i=Stsf`D-E#%lSg_*1Km>@8xv|yTI?^Ii8*n&7q+y"
    b"I(}Jx!}3qLyYl35_7#mnRR}eMceoS}Cg;OT+MA~DYaZAzd;yi_9`FU^*23~xei|g{kJ=_s^X|dw=Xn2&*rjwW>Z_O&99pgePkr`|"
    b"-?Fjpt8g&algaeL<HAy54roEx>lb$}AD{)7e<m_M<;>ub<D(r9VZKh>9aLo=DXQazfFcxmzt_$hV2dCUc36wqkd4Rvo<Y@gEm=0k"
    b"TR|?`NQC#MD@y!OWyNkU^P^kRg(@_D<w;xwsXfDxnTO~MhvJBLH6DjRnD9>LQ-Lw$67sC^v39qL^QgE{>YlY5W+GupVShlb=T-v>"
    b"^t%Wzw!!X#Rq-5Cqm}}}75TjKGh9D58;|EJd7{ah#oa6j4ttWLED%r!_)!*P&Y~WWl;s-{FI3sK#V;0oMc!p&x8oi7B>D*TYXh@A"
    b"rr*So1Afbw=cl0ZaB>k*gBnw)NzRomk%(qU6>^?i_2hfDrtu8MFAaSyI&9sPaWZ3ASg!`ELXd^zYT8qkn%!k#`^#lzn(;(vY2I~S"
    b"%g@ROr}6C^9sc&xVdqYGC|8=Y+d$u*^g0<!Wk+8IWPBkXi_A5aXbbZEZzlOn94%>7%pC0g`I52zoALZG=~=u@vF@dgt~;`KfaWzq"
    b"Y`GMQd>EeVJfX2X|Jz9}s<Hf;07UbFnWKF_j}B$2@aODWxgPz&+p&(&A4vXz71TS-dc+8+p+B}XYMQ$@2_^aKuTM@DY8_YwJU-Nt"
    b"PmI!V25;+>>DWmYj6oRE`!nf~Wp&#dfDKcFEuDfug83)L#-<8d*LV?c@I*Q>k-JTqM?p23#7DyG;VG!zKM$ourlWogtd7H|H?~s$"
    b"WHrBhc=uG1A;rX@!SO|Le7RZP5YpBzj}Ekua_ndEl>C(c#1mEd5R_*+u7}G(IszFh1|eI`KXLltBtKVRaB&asboKk2^4F+vK(Q2$"
    b"C>jtod2JvGEE8W~`CFlF&uS<?&Q1o(spGW8P?<rz6=x4otz>V;&ySH$ou5v8a4_$B=fgEec8ZD*7a4bb!^qs{od{Q2(CYv5hBdI5"
    b"^cloUZ4E^|Jl42$YAQEv7$B3C&C|MjpbHtG&;Z&8!`;IZEyDx0Rt4=2dEo-(VP=JE5HE`Bsg)x|Z=DY->0&d_f(!8V*%_8(%jOn6"
    b"^(PJ9wE!Op@97yCZjG$o*v@k$Hz;>EnU;@(r9HK0HT#N{M%IG6Xv{h4WuEI1nJgZAI+{C=c*!Mu6~Xp$Reg)kFKf5quHYA!OS2`0"
    b"Mw#1E=$VwR?XdPc%3kw*2(vCjksDYS_)2>9WuBMHnGVRDG#^VwE+|Bf-2UAKO}#JS+vK@IKXs<f#<;fCf|!ytPD9l}8&`?E(LUzF"
    b"1Hqzd9V<?GTh?FeBfO}k7Ac)7#|eE@r`~`*&@}4%WQCH<3heAKG}#K!*>|BjIN3hpeW*yl+fZm#Q#g6hS}CeF&qx=PzY@eYqnOdQ"
    b";BjL|9ul`L0p!SGJki=k*w{45N5(zpR>7aLjawBiCF7~EqF7bAU`{unHT112<q67=0>ui>dx!)(BTrKZnP}-nF#9I>Ws@p-<Vo}r"
    b"4R0H9RM$+-D*jz)9v?vv-9Nt?PnPJgYC(m#uwrQTkyZqAuOr?Rzg%IqdutdZ+TAwkBwW*0AhP==Gge6mnE9+BDSELIo|Rt?&;3_e"
    b"eDtf84bsov9EMG(EuSyv(ZZ%ILcGTg4Q{$&<_yuzZkEF`F=Qx;#WMD~&B^5*$EdwBJKS~u)Bn6wUCb9~sP3;AvV!g7102=prh<b|"
    b"<>r>Vo#zp6&rMnBW?h1>cHq_Re&;8HzI{W-j)5Elrm5XeM0fEF{~?&Zv&uo=l6Ja^v38EUZ+g4@hS~Mo*+aiDuhl|Tz+$0-FPI9+"
    b"be=-RYqBQ}pUIgUAqV${X}-<ii}i0--aMOVaOXdNSWWzrQy96k&O5`7%)1g<{tu>`STS|fLbF8n%fh(ildPX@%=|xr8}qX7H7{8z"
    b"jG1q~pLolsoBuf3_(V)wzM-<-GS6_{i8w31>BVH)?e?PK7T26gjC<aPkx#@@oEey$`#pZ|WZCf8xeaY+%vY%9g;v_G=3B1wFTC>K"
    b"6X_27xem%K$8lvE3hIEp=yacJ&h`#>`}aj$?hd@h_fO(91}FffiA<YNX*>RUoc}E!$P;N)*+A9!8n2sHG`lUK3V~rqUVXEcUpM)c"
    b"8`<DV<<a8{CVu?r-lr)^g73d!(#02&S6_|{(AB2tM#ph{eQtEf9Qf1$v{>3lhvLCR4(Tl<GN7Wtj-T_<j&7F^j_~2Bfys&WzA>Wp"
    b"A5EE5@qK(Mf$NZ6)(qw?(UqU1WwL-;Cfg}!kd(C%8ef@#g1OGz*?4}rd+tSHS1p+3$tgyYHg|ZUjQ*1s|97iYL3xvWlz&22baawW"
    b"4VDF+1H7qC<?qbcX<mV{Va{g-`X2iyY662RJ&fCdGy4>ku%Ow5@{5k`1g{H0AlO*t1j0@wANX$PY`bqUlFR@fpEL)}U-F<Q5_M+c"
    b"(9B8P3320uuiEI+)z&u8A4O_yEP+BI>XdVSW_Xrb0LzMaLuf7rxrs*9bwf69?WNv5$!FQ1B6YkrWo=3^-aa+bH*0)B&ZlnmX7xnJ"
    b"Z^0XJ4!SsPl8X~KK*YQMhMTeu<rq(xO}F6Pb{)`9c+YW@mb4|0RO#|-&$*top86l({fKy3Ea0Z$P#PH^m!~T&<s?az+xs&Yjm1%1"
    b"e%ymM_=~Mgs5(Zc5UAblL%jB>c9&m$Zu~s!u-Ynuj)-^E6ID=0b?EpjGe_iy5kUkaG!3ds#J|K%oN}5t;fdc+*{T8BWYhrUjVVgf"
    b"7a2&17l+#8G`+u`uJklD>Mio;?*1w25Kqw*@9@F?_VK#nb#aTp+t2wG&Ku_Cf=<NwL(jxZ9Ea5+{`*L7SrM=M;~B!6pz|w+n{UVU"
    b"8=v44FOIuNMgL!myPt@VH`$K7Jdg^6P$C9==BtnhqY1+6y`T>6mVM(V{JT7ViT?xs14k%U9*2{UUiV({KF+&)%&Sn?GBr8S<A&J1"
    b"S&<c~_{=6yDO`8zwGTYJ=yO@q3*dH9-zr{*yLCLbv7juQg1I1F4|BKi@2kuao*3j=Vf5Yy!`!mL{G8`of?{^KdsF6&Dwy!TnZ$)F"
    b"J|Ac&AIg8^eZ1+$=ed7%m4EhaxN3?ceS_y&2U@t3Lv|8q`;IpM*T`66;x#_{MY~wMpYawq{)PEJuD<OemwP*J|A)^#zhF^S5vu3V"
    b"Y@Z;XQiq1TE3Jvd(tIG-hnqZl@z4h%T)R-`Z+yf%RL+0i@8ON}L*wR+os*MzjwdIlb=r+M%)zmW(JXS4G5+NbSLD*h*;SJRmk)it"
    b"mae)!C9eK??N7$Mpu<VMp!~NKOG!=6ymcnwYT_#C;^Tb0dWCCdkxzd*wPAnXc%Ig7iWkE4#X4raB3l&8<W(>0%Zb5y+|lJz`9wBv"
    b"j^<5^*8ehY6XBt>O1zOkJh8n+zCa5)T2J+7`}2Rmzx!F^RQpd8;SUjb9Dx%2kwpHFp1-!Se}IqXx8c)f`xjj3<72p}ZPls!oA1r@"
    b"H{9A%KK}Y6xO^5Kh-<HjYHImI{D$C_X7CXIXkz>ZQD+}+;Y8j<W#L!c;=e3z+jw#Kg|nQ)C3}4U*NAGeUi&Uj<jsH1|2uwNdS_}W"
    b"uKxb3Z4={H-=kDIoY2%YTFiXAh4e~jLIOWG^(B7|>D9$e_?XA%@X5>oa*?M0$-jEd+Yi^I#`4}~jN$5zO%{rI7D#5l-7!2ZB}UAN"
    b"eDPG^JaV{x6=F|aK9T+I%yq?Y_!`J%Xt|?z`rF7&*5UDYZnQte&rZF;)qEnK;QRA`nZLI?dS%;G`>&8eJi^T!A2tV&_-UqNZZwzJ"
    b"ZNBC<=Gw0C#(eunlP#~NpR0ZSI-b`-{+E4FX5Qe>yOUEMwX{zTcxQX0ed7IJ)pFuqGsAa1q8JhMn&Sl)mB=C15D9|G@sZ4h;0=6e"
    b"3IPVt9&5jmaEJ4o#>dZ2jORzvUrg*@H08GczthuMG=B6&_vu4py#4${K6fox{o>F-BE6Ome@5dN8+Vg`Jiyy0kb@4R3KG46wCBFb"
    b"@ksx4ByWD<zRmaXpSX$tSr}6Bv><73{Dpa$UyHOOowTD`*?wIx)OOdor`?SX@}J<OCiCs?fO~KLJ$C??jpq_y(xJ|`Uu_>UFC@Gp"
    b"iDV&!wY!lI414T;Jco1sCGtDuZyUM2zG36&UiAlmksJKc@gFWY{WnYW-_K-*K6>TDV;}$ZU(|F)0?YqH$GQ?p=xu@Q+2wOqXutEr"
    b"mA&zR^ZA<Nq2Ap;y#K^yIne#`s!e~G`t#wGJ|7@pK}fYNKj<mX?ZTjZzT6`x_oBI>t9HRxWN2Di)O&#Mpq3Oz3w4DJlINFyNRbCa"
    b"P-}lb<U<5T{gI)^fE1L5gd;Xq4XPoMwjv5z2`rC>&{n#&3hC66SU4(TAqv=Mb`>y3QXmvk%5C4;21Z3Wq-2+J33Ljk3adE^a%D$4"
    b"cWDMVmRiM>hf#|UZS}fCKupb85ipe4T@@QG|3gp(a~b0KLl839Sw%g%uUmt-9oXFrVJpD0)hVd4puESHM7{D*)!<1DCmSMr$f~9W"
    b"30`0=z_9}{>bnf{3pX$Gdy?lB^2WvmUK+x*R8o@gLVjEFyg4!J$JEYS;01z~gv(pN3zbqk@#ORs=UqKXrl?2!5NC0GI8Ao7Fr*BS"
    b"^gyhPToK2Tv4;B#K@t|);*N+Xn!y7(IepJGPrVmPhQEU^kJS1MXtsRh++>h4pem^#UJtOBj)7AtJEC=+rLc84>U6Oga)_N0c$R0-"
    b"#VY8LU7EgiMRZ3YOhXrG;6YgV?B?>Lq5!s)v35y15=t2;Itv-HEyckftErD@Iy^$wG_IlC<v+?Cy~GA(SJizMT{;?+GL?o0U>@Qz"
    b">3%tO4~Qn@Qm_N*%r6Q|P``UXGVxQ=b%;FFln{|5FW_+^Lj&>h_ggu{BQGK1DIOlg<YQG{P#Ky$S<h9jz+%$hsIPOZRW9617w|$<"
    b"f^=@sQFdiF_T&u0%Xzn*avt&aqyk>ftAzXGAN5+vD}E1;h5WHqD?qe`rum|orNr7IaNn}vDA>kIt6WO?DOzlS>a(C)h2$2xC(|Is"
    b"vNbDx8;?`@j$`qNFK&oRRr)#&tYWsaEb_#Rl(zcG@3#arC23v^3`)6e)_#D^jvaw`Mzn(WF@AFE^YHtIZ(V)cZt7f3g_1n~dkB=n"
    b"gqIfXb1lTI&AT;O&Zq%ZN!IG}BT|eapJbf^P=RI8MDVNZ;@F?z`uF={VQ{ixkmh|R+KC%!NUem!P=2IJ+_O_sa^6TTuGf#29Nm2s"
    b">TL){bR!)cZw^DK(zhH|53H*>kr?P~A3MJK3Cp)Cr08F?WGG5;+l3d~Djj(ELiEIopC0GA?$P(m;U8SH;Q+ACJ@eprGN9H|rkjpz"
    b"!aR>NiJo2#CXa#k;J}x}s1x?Rqn5*XI1`Tk(>OQp&6VT+U&!x?<_9Qqx!#;;;=ORd*01UnO^6rl%cbRn(_{6KX&>T4pMjazB{0ni"
    b"Plpkmo+fRy?<YLhivqz*Sw{6=Q8f@^>B2J)UrMGn{A1Ho=N1OGb?4@`eDAS6Yd}2?<xXljtof=RYHG3%;_|Z>md6)vXYxy@SR34%"
    b"C4Upr(V8`MC|tUI=T=D$9(+~p$^FxJJM82+rQ6Ec3l7Txa`1nm{IT=+!vB)|>bd7LHQ5B=8Ej3s-=~%+NKQc;@k$ge{?-}_8M*<%"
    b"lZ1B!$~Cp)%<!l0+R3=0eima3q`4H$%myfPcqexf*_v<G*wsWHe<ZgeT}Ra}B#vk+M1eiZdfM(WN{C)1iwX}q5NQV1H}Ti6G$!M~"
    b"8gwlrEsa}9bNvw2w`<`i_4JO?8aqwg_;JLOAsp<2RzPBZ0N7^M^VS;qC6F(9cu^b5PF82m<nVMon`VRYRa#71+S=?ytxJIXvJIYu"
    b"a9Xah9JHI9?a|ioZiqxTgH!FZS}w_%%}c5rM}CFzORAKy0>JH5@CW{yo{MlS_UvA^Iu0~=ttLrXab?s@p4t=*0ZVCGmHxG;6CSd{"
    b"csyFS`!XHP!5Tvfv}U11lHXb;W!?&);QIUEj{=4jUm1m3#|m1Zx-R|2bD4D1N>To14z}Yg9x+%hnB(?NmW#mgaQFyo4frzoyM4G3"
    b"9rksY2fJ~;nOq>q?R>DT3gjw1n19|mtG2}scG<P(OXJiTQMQnY?g*C<-dhxo`FJuN4IRD@B@3=!#+rjW4yTNNp*m5Qpe&Qa{jmQb"
    b"7)S<F%k|%J7dS8V<+9s)-Q+fB4OMKD9n&^*)g>^`!1YdKA?3uEp=ha+f&wo<cq&}iRC;>>@2$D5tL}r-4dCu`UW%lX!HM(slS!oK"
    b"oX_Xf*iQWJ5|E8D7ZQ#<Hk$j2g**URC8!y@N?}H9mHIFK5{COPS%}B%wz*El-@|zeT-9j^r>Ve^y$aTd_FoRSd2VfqAsfLn`5+&>"
    b"rsWo*jLk(m9lx5%65hsY)ly1iCnZUlHgYw$A>H?)@CHZDHdKZ2Sk~j|h(~!A$G6jd@6z2R#)_H@)$!05<^K!u=?N*;`nWICzc$!m"
    b"z%!~%cuzivc;R4%@a}pv8g8_m4JUoI`J6fa+Tjr4wbn__i#B)G;`$NZT<$DfmXF#cXuqYhb-qmY0m54wao|PSNhffB2`@jlH8|OF"
    b"G}`0t`i`%6(l$+6=y<fmxm#{MVCRyES5lL4!*c=YdCgr$Sv_)R!b{=!99Xl=0UTfYccqM0MdMqlM>CnD(GOjNE$Z7~ZR8|~+M>*%"
    b"m_i4VYjO8#kQ%9iA##*{Up=z#lh2~~tPa*}hbQqAzhdDrLh4G;hHuiN^{ip;7w%SgzHg{}J)d{Pf%rlh=`Sl~LC5i}u5m&Xou7+Z"
    b"EPGe|pW^v=7FEFq2yaaU@oeT&e>s!f_k`!~ntQqN+}6WE_=Dq#gBeT8EkufvE)m|nG(LgH@^@LX<*V-`yb=f8xitnn8KyR29v&yW"
    b"Lp>?hwR!8)X)T9@viU>ReBFBC%EHhm;EPK+NZ;EHa%c8yvI(s2uKFo!&P%9u;`p)xkG*vdiAi>a_$jr`V>do>mUSsT_vBc19T<;("
    b"y{zU3_6yM|M>y_;>u%<%a*|J-EOiHg@o`~rm;i5I1gJO3t4CMgsG@%afqh*od#V~c%2D1wcA)p+itd+pW??mw9K~mK;KZvE160aH"
    b"&hlJLcI_mzzbzVm;F<;;!gE<W8ek3;jl8kBsj1iQeehdWT-j1}_RzoV)@x3qo~w$IK1@`{NraH*<EjjGangK}s36OvE`Ljpkw`xr"
    b"PD0|SkE(vHMMZ$W8aTCe@v%_SpYywietd9+y%$MBJ6aY}0*ghoR5*ormW)Sf!V+@(NJvBkSjkut6&<>LUvWg~!f$1M2c__X_0Gr0"
    b"_7@L+oR_PX>OM*d-*lA112qw$_>}1N7A^)sqQ*j*Ol1^FMR?6##w|X%&+;eV?H-=0&wji$m|ME*y$L5CZmXtCi|<lRK}oB?Z|p}D"
    b"rz#58rEz@paow*|QH_4GIZFLPlac%kR~B~JJpnE|opp&^d2-;Q7GL~+HR=1?4RI|`%AOPeO@a*RXK6o$PHZoRAqum@YpO2d9g`Zn"
    b"2)R`<B!>d~?WHX{9TPUBZJqKiw@wEX%QI2wgqLLJpyJp~x3$G6)ud4-(Y=Vz=y>$X{hNZD?4&KFjhK~^%Qi&cC6lJEOp!lA*ch5u"
    b"a>j}}kgzkTV+!LcTe6pK&Lv@*Ni5(?TG1|lt?h%aY4zvlc31ZH?(*fglTndupAuawAfN<kR}&w(GCX(;sU&K>1N-;k0GB>&!@e8d"
    b"1x@TLY0!P3?+;sQE$XPxgjpxECz{VDS5N(Su=>Nh1}5G}(p(gUnle{KKjMsb7MChq577bq!O>*PD<%nH-7gkKe_FRUUIljffXl2{"
    b"d}6dO=6kWxww?m{<eQ>&M;w%J!U}0SCoD8@ST|w^GBDB6tV2wbd_VPWrF73O@-4S(;+5ll00$=UX?4SR%i`|QV-x`Ya_e}9*<m7c"
    b"1udF;+}?hGD@@HbI`PCyUsAD;?E6tWnfL`2L8QwG6NPKiS7EdD5wc4TzFToa&1`V{GN)OH;{L(m9VQ>JqB-Q&+2``x_jA-z-*5jQ"
    b"!GFaka%^lQpU-pm0kwk<a&cYVfg+kLh5*R%yHY;ZrP{HoZafg7vuM5eT8B`lr2j!Yq}inEBtziqhx>7v=B4skSgfO-^;gPrA|%HT"
    b"2J<Ws1MyZxYWIX2)Z7nK-(PG87M@2u)vNRJ1D^B8qvXHo6AluSzee7d;a5G+D9@{ds0zCV`R90ESrdY;%|UtJMe{-!`GmxVStwll"
    b"Dm2-uC84;nxm}iy<KWbOROJ)4V8y6hp5b4^B~dT2H2y0AYR?)-;$PQ5DE<gqhx;!4v?~nOqSMSRi-i*zXzW~W$%qH09kk=HNZ`R*"
    b"qr_&P;pa>Hf;$kegzz53fBSmkR5@MkYYImUBQ^T6GTyc9#LLS%BagYLqBeoCafOGMuw+yw=2?vJmf=6(3Jt8cWCuz-IfWY7J@f;<"
    b"lfF5yERy_72hw}Gd&5w@7OL-8L;ETv_=QihRl-B@Wu>WdXMc)5fxAV;f2Cd=m`dU?4dSm9(^m%UDSu_h`gQg4_bT3PK3gH(1LH}b"
    b"wig~k{raI+v%|@zm#FoPxri#;{i&*OQ0=g@>E%I{^>(DAs@!2@>r~XhWXp+HMdqlPr~Gky!~HTl{Pj!^vZs6G@zLh+lFhpzKOeO<"
    b"!i%Vfuf*}AR)6ZgNU((P5H`~_m|mvJLq@h*?Lj=-&LN(hvHgBvKbHIt|4BU+n60$$oos$g+j0={C=(BLI45^3Q7w+z2f(puJea3u"
    b"em<Cvl*ruZf53MR@eEFQs22NspyO8;LI0h4DzdTvh&xewmVLc_?k7i}_3Iv9=6}VP5#Ejh-VQ4B^z$LyU&PBkpyuvY5wERk3E>58"
    b"Nse|qdM)KXNiTwHj9!GVHU>L-pg7+Q&mo@NzqM+KSic>R!1)4xlixA2FQ}KQOG;>bgx8irYu*h)C<p7l4f1iwmrnGa`1be8SdS|3"
    b"XnZ!}sXUvmT2dzF8=X??&!RFjsqR8NWzAZ(#BkD8kusH2C-Ycdf#%$**tcQqRc+#xxxJ^peRXZ*h@3QOz7e(FZd+C&soC^>OG@R8"
    b"k=hYNylxzHqU3cWiQ@~aOyC72IUTd(vZlk!wX3SW4RcRxIcN8o*3K7#M^RKr9j)0NQ7dTVq9rysPvZI^O{N})c}o2de=9mrVx`!m"
    b"RgDWN@aEbq6|+JysAX*vf0wqBb4Z+SC~fP6vfuekic2)#h&9)^7A-L#`y`IQP&=}J1VLYYj<rP->c#EskE{pbD;{2%!FHgr977h&"
    b"T3=3st#nA6scS_iz;7uJnWW+jc=wr8^z-=S<V5k7>XO_R4f5Tbe@sm_=n>&6ZjO}?9kB0HB>l(>p${5PAC}|DszQ1wLy30vu)UI_"
    b"8R!3Pdn>HS!q1tjUO)*K?I44ns#fo+7?rPABU?IiE)b{_q1<Yv6AMHZ{^(a)sI2=U@<eS*Ob@*TtTA654R+^vHlYsX6F7v<LAu=y"
    b"c2ghj#D|x{Nc1R;%nt74&1m<~P~LQnko@KY5DUy-_zv3PWp)uyQ`HVD{zKvE@{tqmapb#;pq@1s!mgsfx;Iyp_mbygLp~37Y~Jt#"
    b"kPaO7e-QM8Z9mI=wg#FWT8+#qB!{5T(p<=EpJfaADPlD$-z(w?cO>X?ssZ^=GSD6Om*hkKwvi*7lm6;tvSX0g66#V^K{+&&!6d5s"
    b"lb1yblOr#a7@Q8lN2|OL!r@N_)aTy_L|5AJppE0L-b0~hKKQA&910bgrD6h6V=)Uvqqv!RbFlCiBsfwr0bWJPoJ5wo;%J$&d&Q|#"
    b"IpXQZkWFrZu22YWsT>uX`H4Op-giI}>tHLSYbBH3_$Wbph2N*F-*76HP0H1=P)sFFDHN*pGBG{zpY^JIi>NtNBK;CbD-OVS+Wwtr"
    b"Yb|zT8c(V4pI#YT+7!AB^2!u`ex;ur%8I9m1%x){6KyO&R`DhNisNAvBa6Kp!rAR6Sc*Or(C68ag@JCUmL$R>H8&fQ0%ED_0$!DS"
    b"3Xkf@C1i)J2fJEDb3%w8n4NmYY=u-zm}~nKz4Ih$#CuZyWQ2tLJrut-lL;m2x#N>L{D2nMS&pIo#Kib6&BAO|;3U%09MWvNN3GKQ"
    b"v(KH=3q2;*!_7%Ernp1-(rt~3I&++(enFWQzg^roZ~OgGJJ6tjZJnwNLim~F4&l^A7P0&$JPk$T+7dgzNV2M+vIY+?%c+*Y3l&_>"
    b"p&|tY(hAEsD3QsXjG9j|PsF+do+?@Q!B+*|b`Nij2cxS;#eMiXN92jHtPzLo@-!?ye`|7!H{SwYP_p8XFbMBl0Z%W4I#U6UP>9N8"
    b"v-?2L*|@+?im{1yp8p0P8E7h|CH{mb#`3y{SA}><Jdavbc-RFV6t8%_PDpjgFn^>~WO{VubWqLw=AACqTFVV~1@Tm=!9lz@+V7}#"
    b"5Z+q(4xtS453FW`yv{!6bMBO?<S>J~C3ZlSjykm{52Gv_mPId`waf01D8+tY#dRGf(1!Rmc&`-kUU9b1HMFRlttu6GcSmo3T4tkG"
    b"dL_WQ%_^+AGu}MHGeDIxPVHO+MOs#C5jEByxFg<BJPXzXA2~j_>(|Y<<gZj4@oWb?ypR_Iay58|`62<QAT#G9r7m{Y9rt7CJ4T6%"
    b"c#EVVNBB<V>~^`(xA6}90ZP0yYvs=St98|Ry2|BWa!ZY%2>edx)9*D+a{f9qlxmgc`v&3}v+!=n`Rd=|pWaX#8y`w!AEv9msUQSO"
    b"O2PK&{%RY}C#G_V(L$KR1f}ZlqgrQ%8WHn--O&h7>fi2Vd0&yIxVwMk9g0)ud^|ch%v~3az8cnx(~jA*+f~lo?c@325!JAR(wnp&"
    b"7LJeFGZP-%X}$qvx7rJ^=(LV}I2_P|>@%71BM{Bk1JqoKI;`UtCsf-AO22G<VQvlL_3tPXD}6<3@-a8WY&n~7AeA;<>S__}Iw*Hg"
    b"(X*Mj%bU-~{*K(MC3ZF_xlY~O8VARhRt3G>Q*wvLfn`TKM+r}ze@A+;9^U1=s@mICsolZxr4TRW@xOaY?m&MLxUfsL#Rb`&&qwRS"
    b"$xArC)FPP|@zV2tJ)Qx{8kIsu4Jd29BR$t7M?O&O^dewM#M?pqD(dkA^$zrGfK+<FlQ|rSId{Cb=eBHIsaEY;)nYWh|Ax4i77M()"
    b"=iX`k)JQCG4uzv`MJDfrhvzN(W7V!J;MF2tkGFnn?tnKns7+j`JPU!cY6vA-T!qn%_ox+hsnW3fIYcel?0?gxK*32qIcbu~n#&aM"
    b"CUdYh;i8OEr+6;mB=|`V&%bMzb}4~i%xj1hf^~VTaP8@Fe#L~12sZBZwrd*W{G9CJ3Ga&*5;3Q&AnBCRXojJ3(XCTSvvSU>mj|i#"
    b"u5I!NRW!^xO4N={E>Xt@+-=?2WsP~BPs^VC@Q1_EF{chVg=wIa807q4m2B8I&w_wj5s+tRtS+=Z6W{;QQWBQ>ab({~o;Unsb;BR@"
    b"xhI)L^t?tC7AQABpH}UXpDE`9MLZ@H0exD&C3C|6qwImsqw3hnod@1+mOncHf$%#XKgc1miCbxAs~puz3)EwZ5`p^zx*g^*gHjl#"
    b"9aGs2{nP5H9U_ODJbDb@BxGoakGWPfN9$MaJ(PuJ8P_rGSE9~(P0vj57!aNY5h3+u-IMJC&(a%`h(~)<__gSzcd96?YoI(9Kuydm"
    b"4v~%dokFJ%#G|?)vvNvBCa9%bg;iB_(F7CfZQaWTq6e%Rk!Grh2x?1>#~N+;PiCalpQIQD8|_E>+Uk_eFW?>VZuQ9lRWX<HNi1V?"
    b"hlSdy1X&5bVu=@A^*cx6FlMccuU1dM<Ei)oYDJl_4cH;$i+pM=%#V}KApy18vSNXx1|hcbo3J$F3kl7tOroCY$7l^Ry)jf&<6y%B"
    b">$<m4i}s2faxGtyE`?<+CSRn+KvglgN^@BtQ4|9H?Mb`j70@DK-B5+SK;FwmmgZ;cwNMP#Hl2j^F><Fq-k_yrYNryaI2=RMOE_@@"
    b"N=)^VKhzP@$^)>!N2!y~Medhqd`7^q#4UfRA0C5al=p!;&HW;?#t-3~Pp9r`HT6NN27`DVM{t!H{0XgM*i%}Ac9{;Ed|K$jfhsr*"
    b"&5AY$S0@GMV#~$$>|bw$$bnm(mIyCaQy(KGe2F8G6u@`=vDe9ri0I*$Q}i48te}&Cp9;z}&`f;mj+|TXMQuN|o*KMJ>e=-C)o9YB"
    b"w(J&oQi>7+>C;TyRtxI+I2njhPsZvLm7WYRO9HuG5YUf4)C)?gJ)ejn6zqZxt7|F7pYTxAKhUJod?A^Em_Gszp=<0i;$`6h#M2P("
    b"utbaoS3+9fp^My4|KmSf5KCH;KkVCmfSLj5TSTqPO#w^VAUcMWm$Hez2&!{5j*i|e$fMSu9b`v<`PS4!EP+;kh#i(M$4ZaNwl=>k"
    b"R!IRB{wmnLOEeeo)Z7i0wPYPxmB30v6b}(lFES??4rEs)n)ia(OQ@BtzJ$V%i%4=#&#giZ`mI&CgEsj655gYCEb^s;VkwAgEfJ}N"
    b"AeW*+XZR5hR3AK+@>RhWAG=8I^EyP;6g;6c1hK&W`94}k=4Tz+QN)XbRpD$A(JHof6;RV=5k}^5e8soQL-Bp!B``+iS9_HJa~U;B"
    b"U?+i{P=HF;De$sXNTIc~W>ipP$V);ZU_-MtkutkW1X&nW>X;nXHNhG8vQT7k6)c22vyOq>8OGh0X#kYPC546YXMp{kQlEKFu@c#b"
    b"=xAz-Ei!+cK`&^dx@5RMO6f_lh_W|A)m|wcNw$uO^g7YU(N^=gTJ=%esG@)!`{mJSJj8Imu6zV%9MLKJ&*(tBbTYYWSG~Vk4UqXX"
    b"udMDN94Tvtg_0<_KzO!iiaHwE_hK6@AC+n(Mn>f*k@y$)P{0r|EZevE0xkqv?s44+&5<Y{$yl!)g@6P`g?%yv6(y>*9!dj{DcomJ"
    b"#zYBFP>~*^kP$g-l!}sLGH!MUXbt!-ZIu$Wj2K8Cu#9EQ$KTm_KE6+7*kZUe>rvYip*P^A@&^JIamZB^q5=VpriOU)5U&g1E~7aB"
    b"YjJYMayuDe-)Y|br@fX$c*kN}DWD6s#z3PKSlM7_z{BgH1OBpT-w=2{Xy+o;i6$C(mk+AJ3P3e73`24p=+U&=KMmrhN>C%EdXIrG"
    b"Xl;vuzc;NRHM33}-%15nTZ)~6f|8XwLdpAz2+}&;>8xT_Pzu*sp+E%eRYs@uRLQ!dvZ$LQnyYHQXpF4+ETbE!4xwuGk`i6KADUe-"
    b"g32<n1|Y{rs0{R;vMne*es|qVbRMmO`E8&POxvx8iY9ip*N<#}+F12||B5&dUh$^+M3A^ir^_DdVGYtc3$6eK$)%?YSNK(^j?pvJ"
    b"86>yTPjP5U!Sr1y21-k-Xtr7g(1(lF&__wae%sHQs9aWL`dUi!0-n^+tSTj&iEA3SRWhQNOP(`~HHb<yTf1g?dO}42X=Ya5*M|<9"
    b"sk>v`smcbE4Z4)`E4O%#{KX0Y>DhQav+MZS-cPYx)or46!4~v8;mwSXxY9HmgPZD0F(g_aD2P-pJXU*+UNG4AJwjl#Y!+R!86uXd"
    b"f|l&2$^HKT00000000B*0000100000000E60000100001000EA0000100002000EE00000000B>"
)

# Reproducible AmigaDOS modification time of the reference release:
# 24 September 2026 00:00:00, represented as days, minutes and 1/50 s ticks
# since the Amiga epoch.  Fixed metadata makes every patched ADF identical.
RELEASE_TIMESTAMP = (17798, 0, 0)

STARTUP_SEQUENCE = b""";c:SetPatch >NIL: r ;patch system functions
Stack 6000
SR2_SPLASH
img.cru
Echo ""
Echo "KS3.1/AGA/060 patch 1.8.1 by Timo Heimonen"
Echo "(timo.heimonen@proton.me) - 24.09.2026"
Stack 6000
SetMap usa1
SetClock >NIL: Opt load
Addbuffers df0: 20
Street_Rod
LOADWB
endcli > nil:
"""

# Embedded 1.8.1 helpers; no assembler or external packages required.
PAYLOAD_10 = bytes.fromhex(
    "2f0247fa01344a6cbf766700009c4a536710202cdf4a90ab0008b0ab"
    "00106d00007c203900dff004e088024001ff0c40012c620000686100"
    "00804a406700ffd02c7800044eaeff886100006e4a40674427410008"
    "d2872741000436bc0001302cbf9cc1fc003041ecbf9ed1c0226cfb9c"
    "700b22d851c8fffc203900dff00402800001ffff52802740000c4eae"
    "ff82241f6000fef64eaeff826000ff742c6c9c584eaefef26000ff68"
    "42532c6c9c584eaefef2241f6000feae222cdf4a243900dff0040282"
    "0001ffffb2acdf4a663c2002e088024001ff0c400008652e7e000c40"
    "001e630e0c40009665200c40012c621a7e014a536710200190ab0004"
    "6b0c66044a476706600870014e7570004e75200190ab0008b0ab0010"
    "6d0c6e06b4ab000c650470014e7570004e7541fa000c4250426cbf9c"
    "4e754e71000000000000000000000000000000000000000300000000"
    "00000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000000000000000000000000000"
    "00000000000000000c800000000666260c904650533d661e0c28000a"
    "00056616700010280004610001024a80670841faff9020804e757e03"
    "2c78000443fa011a70244eaefdd84a80670000de2c4041fa01142208"
    "243c000003ed4eaeffe22c00670000bc220674014eaefe564a806700"
    "00a8220641fa00f72408263c000000854eaeffd07a00220641fa0180"
    "240876014eaeffd60c800000000166487000103a016a4a0567200c05"
    "0001660a0c00005b66107a0260d00c00004065ca0c00007e62c47a00"
    "60c00c00001b66047a0160b60c00009b66047a0260ac6100004e4a80"
    "67a42e0041fafeda208720075780c0fc000541fa00fed1c022062408"
    "76054eaeffd0220641fa0100240876044eaeffd0220674004eaefe56"
    "22064eaeffdc224e2c7800044eaefe624e750c00000d67200c00000a"
    "671a0c00003165180c00003462120280000000ff04800000002e4e75"
    "70034e7570004e75646f732e6c69627261727900434f4e534f4c453a"
    "000a53656c6563742064726976696e6720465053206c696d69743a0a"
    "0a20203120202031362e372046505320202864656661756c74290a20"
    "203220202031322e35204650530a20203320202031302e3020465053"
    "0a20203420202020382e33204650530a0a507265737320312d342c20"
    "6f7220454e54455220666f722064656661756c743a2031362e372031"
    "322e352031302e3020382e3320204650530a0000"
)

PAYLOAD_23 = bytes.fromhex(
    "2f0e41fa004c10b900bfde0008b9000000bfde0043fa003e4aa900126608"
    "41fa0014234800122c7800044eaeff4c2c5f70004e756112103a00180000"
    "001113c000bfde0070004e754e55fff46000fd5a00004e71000000000000"
    "000002000000000000000000000000004e71"
)

PAYLOAD_0 = bytes.fromhex(
    "48e77efe48e7fffe2c7800044bfa00244eaeffe24cdf7fff6000cc9e"
    "2f002c7800044bfa00264eaeffe2201f4cdf7f7e4e7541fa00244e7a"
    "10022081f4980081000080004e7b10024e7341fa000c2210f4984e7b"
    "10024e73000000000000000048e7fffe41fafffa41e8cc5070092210"
    "e589204151c8fff845e807842017206f00204e924cdf7fff24482400"
    "4e754e71"
)

PAYLOAD_42 = bytes.fromhex(
    "205f48e73710267c535232303e2d000858884ed048e73f304caf007c0024"
    "b4436d02c543b46cd70a6c04342cd70ab66cd7106f04362cd710b6426d00"
    "00b8b86cd70c6c04382cd70cba6cd70e6f043a2cd70eba446d00009e9a44"
    "cafc0028c8fc0028266cfb94266b0004266b0008d7c43e02ea4f3003ea48"
    "90473240e54f0242001f70ffe4a8240046430243001f70ffe7a826003009"
    "6602c48378033005e20e642441f30000d0c78598320967105341600620fc"
    "ffffffff51c9fff88790044000286ade60264682468341f30000d0c7c598"
    "3209670c53416002429851c9fffcc790044000286ae24682468347eb0fa0"
    "51ccffaa4cdf0cfc4e754e71"
)

PAYLOAD_45 = bytes.fromhex(
    "205f5488b7fc535232306708b7fc53523231661e0c6d000f00106610b7fc"
    "535232316720267c535232316006267c535232302f0841e8321a4e90205f"
    "302d001054884ed043ecfb303347002433460026006900010020137c000f"
    "001e41e800244ed04e7148e7303043ecfb304aa900086600032e4a29001c"
    "660003262069000438107003c044660003183a2800020c4500806200030c"
    "70001028000553406b0003000c400007620002f845e80008221a02410003"
    "660002ea51c8fff4e74c2011675a20404aa80010660002d64aa8002c6600"
    "02ce4aa80020660002c64aa8007e660002be20280008670002b620404a90"
    "660002ae4aa80008660002a64aa800106600029e302800145240b0446d00"
    "0292302800165240b0456d000286362c2450534345ec24103c3c7fff7eff"
    "301ab0446400026e321ab24564000266b2466c023c01b2476f023e0151cb"
    "ffe23607964630035240e54848c0220f9280048100000100b2acf12c6500"
    "02389ec0264f3006e548244f94c0203c7fffffff303cffff26c051cbfffc"
    "48a703004267362c245053434dec24103016322e0002588e4a43660641ec"
    "24106002204e381098403a2800029a417c014a446c0444447cff7e014a45"
    "6c0444457eff3f03b8456d0000643604d96f0002da4534059444d8449845"
    "444447f21400b0536c023680b06b00026f04374000024a426b1cb0536c02"
    "3680b06b00026f0437400002d247d444d04651cbffd0605ad445d04651cb"
    "ffda9046b0536c023680b06b00026f0437400002603e3605db6f0002d844"
    "34049445da459a44444547f21400b0536c023680b06b00026f0437400002"
    "4a426b0cd046d445d24751cbffe06008d444d24751cbffd6361f51cbff22"
    "43ecfb30700f905f1340001e08a900000021202c24102340002422290010"
    "67062041214000142c6c9c584eaeff1c4c9f00c09e4647f2640043ecfb30"
    "2c6900047a003a16ccc53f074fefffb8204f45ef002412290018342c2452"
    "7800b82e0005641a090167123004e548203600080902670420c0600224c0"
    "524460e042904292204f45ef00243607301b321b3800ea4c0240001f74ff"
    "e0aa3001ea48904446410241001f7effe3af2207e54c48c4d8864a406620"
    "c4812c482e1e6708224785b1480060f446822c4a2e1e67462247c5b14800"
    "60f453402c482e1e67182247d3c485993e00600622fcffffffff51cffff8"
    "839160e4468146822c4a2e1e67142247d3c4c5993e006002429951cffffc"
    "c39160e8dc8551cbff724fef00483e1f5247e54fdec74cdf0c0c4e754cdf"
    "0c0c3c2c2410200648c058974e75"
)

PROGRAM_PATCHES = (
    # Original file offset, expected bytes, replacement bytes.
    # Select the driving FPS limit in the current console before original runtime initialization; replay argument setup
    (0x14c, bytes.fromhex("24482400"), bytes.fromhex("610033a6")),
    # Clear CIAA DDRA bit 7 before reading joystick fire; preserve all other port directions
    (0x11746, bytes.fromhex("00400080"), bytes.fromhex("0240007f")),
    # Keep LINK and the original stack guard, then return D0=1 success from the manual check, as in the user-supplied patch
    (0x35bf8, bytes.fromhex("48e72300554f"), bytes.fromhex("70014e5d4e75")),
    # Queue original music tick at level 1 so Paula level 4 can interrupt BeginIO
    (0x10fac, bytes.fromhex("4e55fff4"), bytes.fromhex("6000025a")),
    # Select the first active BPLCON0 in the KS3.1 AGA Copper list for four-plane road; retain six-plane cockpit at the split
    (0xa3a4, bytes.fromhex("6706"), bytes.fromhex("671a")),
    # Apply the selected 3/4/5/6 complete PAL-field minimum interval with beam phase and safe raster publication
    (0xa4a6, bytes.fromhex("4eaefe802e00"), bytes.fromhex("600000ac4e71")),
    # Clear publication history when initializing a driving display and replay original buffer-index reset
    (0xa01e, bytes.fromhex("426cbf9c"), bytes.fromhex("6100065e")),
    # Store the complete allocator pointer, then test D0 as a long
    (0xb750, bytes.fromhex("48c02940fba0"), bytes.fromhex("2940fba04a80")),
    # Store the complete allocator pointer, then test D0 as a long
    (0xb764, bytes.fromhex("48c02940fba4"), bytes.fromhex("2940fba44a80")),
    # Enable the MC68060 instruction cache after LoadSeg through exec.Supervisor
    (0x148, bytes.fromhex("48e77efe"), bytes.fromhex("6000334a")),
    # Restore the incoming CACR before returning to Kickstart 3.1
    (0x32c, bytes.fromhex("4cdf7f7e"), bytes.fromhex("60003182")),
    # Enter the framebuffer-verified 68060 covered-span optimization
    (0x1ce74, bytes.fromhex("48e737003e2d"), bytes.fromhex("6100419e4e71")),
    # Restore the A3 batch marker with the original saved registers
    (0x1d02a, bytes.fromhex("00ec"), bytes.fromhex("08ec")),
    # Use the KS3.1 graphics.library 40.24 Move-compatible tail inside covered-span batches
    (0x2192a, bytes.fromhex("4eba321e302d"), bytes.fromhex("610032b44e71")),
    # Fill the game's convex AreaEnd polygons with the CPU, reproducing the outline and fill pixels
    (0x2173c, bytes.fromhex("3c2c2410"), bytes.fromhex("61003506")),
    # Skip AreaMove/AreaDraw/AreaEnd after a CPU fill; the fallback resumes at $22458
    (0x21740, bytes.fromhex("200648c0"), bytes.fromhex("60000088")),
    # Call the direct covered-span fill instead of FUN_00001798
    (0x1cea4, bytes.fromhex("4eba40d6"), bytes.fromhex("4eba4182")),
    # Call the direct covered-span fill instead of FUN_00001798
    (0x1cebc, bytes.fromhex("4eba40be"), bytes.fromhex("4eba416a")),
    # Call the direct covered-span fill instead of FUN_00001798
    (0x1ceda, bytes.fromhex("4eba40a0"), bytes.fromhex("4eba414c")),
    # Call the direct covered-span fill instead of FUN_00001798
    (0x1d06e, bytes.fromhex("4eba3f0c"), bytes.fromhex("4eba3fb8")),
    # Call the direct covered-span fill instead of FUN_00001798
    (0x1d084, bytes.fromhex("4eba3ef6"), bytes.fromhex("4eba3fa2")),
    # Call the direct covered-span fill instead of FUN_00001798
    (0x1d0a2, bytes.fromhex("4eba3ed8"), bytes.fromhex("4eba3f84")),
)

HUNK_SIZE_PATCHES = (
    (0x3c, 0x17c, 0x261),
    (0x9f60, 0x17c, 0x261),
    (0x70, 0x6c4, 0x6df),
    (0xf6f4, 0x6c4, 0x6df),
    (0x14, 0xcd3, 0xcf7),
    (0x144, 0xcd3, 0xcf7),
    (0xbc, 0x1711, 0x1750),
    (0x1b3cc, 0x1711, 0x1750),
    (0xc8, 0xd8c, 0xe78),
    (0x215ac, 0xd8c, 0xe78),
)

HUNK_PAYLOADS = (
    # Descending original file offsets keep earlier insertion points stable.
    (0x24be0, PAYLOAD_45),
    (0x21014, PAYLOAD_42),
    (0x11208, PAYLOAD_23),
    (0xa554, PAYLOAD_10),
    (0x3494, PAYLOAD_0),
)


class PatchError(RuntimeError):
    """A source validation or patching error safe to show to the user."""


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def _long_offset(index: int) -> int:
    if index < 0:
        index += BLOCK_LONGS
    if not 0 <= index < BLOCK_LONGS:
        raise PatchError(f"invalid OFS longword index: {index}")
    return index * 4


def _get_long(block: bytes | bytearray, index: int) -> int:
    return struct.unpack_from(">I", block, _long_offset(index))[0]


def _put_long(block: bytearray, index: int, value: int) -> None:
    struct.pack_into(">I", block, _long_offset(index), value & 0xFFFFFFFF)


def _get_bstr(block: bytes | bytearray, index: int, maximum: int) -> bytes:
    offset = _long_offset(index)
    length = block[offset]
    if length > maximum:
        raise PatchError("invalid OFS BSTR length")
    return bytes(block[offset + 1 : offset + 1 + length])


def _put_bstr(block: bytearray, index: int, value: bytes, maximum: int) -> None:
    if len(value) > maximum:
        raise PatchError(f"OFS name is longer than {maximum} bytes")
    offset = _long_offset(index)
    block[offset : offset + 1 + maximum] = bytes(1 + maximum)
    block[offset] = len(value)
    block[offset + 1 : offset + 1 + len(value)] = value


def _put_timestamp(block: bytearray, index: int) -> None:
    for position, value in enumerate(RELEASE_TIMESTAMP):
        _put_long(block, index + position, value)


def _block_sum(block: bytes | bytearray) -> int:
    return sum(struct.unpack(">128I", block)) & 0xFFFFFFFF


def _set_checksum(block: bytearray, index: int = 5) -> None:
    _put_long(block, index, 0)
    _put_long(block, index, (-_block_sum(block)) & 0xFFFFFFFF)


def _name_hash(name: bytes) -> int:
    value = len(name)
    for character in name.upper():
        value = ((value * 13) + character) & 0x7FF
    return value % HASH_SIZE


def patch_program(source: bytes) -> bytes:
    """Apply the verified MC68060 HUNK changes to STREET_ROD."""
    if len(source) != 270116 or sha256(source) != SOURCE_PROGRAM_SHA256:
        raise PatchError("STREET_ROD does not match the supported original")

    result = bytearray(source)
    for offset, expected, replacement in PROGRAM_PATCHES:
        actual = bytes(result[offset : offset + len(expected)])
        if actual != expected:
            raise PatchError(
                f"unexpected STREET_ROD bytes at file offset {offset:#x}"
            )
        result[offset : offset + len(expected)] = replacement

    for offset, expected, replacement in HUNK_SIZE_PATCHES:
        actual = int.from_bytes(result[offset : offset + 4], "big")
        if actual != expected:
            raise PatchError(
                f"unexpected HUNK size at STREET_ROD file offset {offset:#x}"
            )
        result[offset : offset + 4] = replacement.to_bytes(4, "big")

    # Insert in descending order so all offsets refer to the original HUNK
    # executable, even when several earlier hunks grow.
    for offset, payload in HUNK_PAYLOADS:
        result[offset:offset] = payload

    if len(result) != 272480 or sha256(result) != PATCHED_PROGRAM_SHA256:
        raise PatchError("internal STREET_ROD result verification failed")
    return bytes(result)


@dataclass(frozen=True)
class EntryLocation:
    block_number: int
    parent_number: int
    hash_index: int
    previous_number: int | None


@dataclass(frozen=True)
class FileRecord:
    location: EntryLocation
    data: bytes
    data_blocks: tuple[int, ...]
    extension_blocks: tuple[int, ...]

    @property
    def all_blocks(self) -> tuple[int, ...]:
        return (
            (self.location.block_number,)
            + self.extension_blocks
            + self.data_blocks
        )


class OFSImage:
    """Minimal reader/writer for the exact DOS0/OFS operations used here."""

    def __init__(self, source: bytes):
        if len(source) != ADF_SIZE:
            raise PatchError(
                f"source ADF is {len(source):,} bytes; expected {ADF_SIZE:,}"
            )
        self.image = bytearray(source)
        if self.image[:4] != b"DOS\0":
            raise PatchError("source is not an Amiga DOS0/OFS disk image")

        root = self._read_block(ROOT_BLOCK)
        self._validate_block(root, T_HEADER, ST_ROOT, "root")
        if _get_long(root, 3) != HASH_SIZE:
            raise PatchError("unsupported OFS root hash-table size")
        self.bitmap_block_number = _get_long(root, -49)
        if self.bitmap_block_number == 0:
            raise PatchError("OFS root block has no bitmap")
        self.bitmap = self._read_block(self.bitmap_block_number)
        if _block_sum(self.bitmap) != 0:
            raise PatchError("invalid OFS bitmap checksum")

    def _read_block(self, number: int) -> bytearray:
        if not 0 <= number < ADF_BLOCKS:
            raise PatchError(f"OFS block number is out of range: {number}")
        start = number * BLOCK_SIZE
        return bytearray(self.image[start : start + BLOCK_SIZE])

    def _write_block(self, number: int, block: bytearray) -> None:
        if len(block) != BLOCK_SIZE:
            raise PatchError("attempted to write a non-512-byte OFS block")
        start = number * BLOCK_SIZE
        self.image[start : start + BLOCK_SIZE] = block

    @staticmethod
    def _validate_block(
        block: bytes | bytearray,
        expected_type: int,
        expected_subtype: int | None,
        description: str,
    ) -> None:
        if _get_long(block, 0) != expected_type:
            raise PatchError(f"invalid {description} block type")
        if expected_subtype is not None and _get_long(block, -1) != expected_subtype:
            raise PatchError(f"invalid {description} block subtype")
        if _block_sum(block) != 0:
            raise PatchError(f"invalid {description} block checksum")

    def _write_standard_block(self, number: int, block: bytearray) -> None:
        _set_checksum(block)
        self._write_block(number, block)

    def _directory_hash_size(self, parent_number: int, parent: bytearray) -> int:
        if parent_number == ROOT_BLOCK:
            size = _get_long(parent, 3)
        else:
            self._validate_block(parent, T_HEADER, ST_USERDIR, "directory")
            size = HASH_SIZE
        if size != HASH_SIZE:
            raise PatchError("unsupported OFS directory hash-table size")
        return size

    def find_entry(self, parent_number: int, name: bytes) -> EntryLocation:
        parent = self._read_block(parent_number)
        self._directory_hash_size(parent_number, parent)
        hash_index = _name_hash(name)
        current = _get_long(parent, 6 + hash_index)
        previous: int | None = None
        seen: set[int] = set()

        while current:
            if current in seen:
                raise PatchError("cyclic OFS directory hash chain")
            seen.add(current)
            entry = self._read_block(current)
            if _get_long(entry, 0) != T_HEADER or _block_sum(entry) != 0:
                raise PatchError("invalid OFS directory entry")
            if _get_long(entry, -3) != parent_number:
                raise PatchError("OFS directory entry has the wrong parent")
            entry_name = _get_bstr(entry, -20, 30)
            if entry_name.upper() == name.upper():
                return EntryLocation(
                    current, parent_number, hash_index, previous
                )
            previous = current
            current = _get_long(entry, -4)

        display_name = name.decode("ascii", errors="replace")
        raise PatchError(f"required file or directory not found: {display_name}")

    def find_path(self, path: str) -> EntryLocation:
        parent = ROOT_BLOCK
        location: EntryLocation | None = None
        for component in path.split("/"):
            if not component:
                raise PatchError(f"invalid OFS path: {path}")
            location = self.find_entry(parent, component.encode("ascii"))
            parent = location.block_number
        assert location is not None
        return location

    def read_file(self, path: str) -> FileRecord:
        location = self.find_path(path)
        header = self._read_block(location.block_number)
        self._validate_block(header, T_HEADER, ST_FILE, f"{path} header")
        if _get_long(header, 1) != location.block_number:
            raise PatchError(f"{path} header has the wrong own-key")

        data_blocks: list[int] = []
        extension_blocks: list[int] = []

        def add_pointers(block: bytearray) -> None:
            count = _get_long(block, 2)
            if count > POINTERS_PER_BLOCK:
                raise PatchError(f"{path} has too many pointers in a file block")
            for index in range(count):
                pointer = _get_long(block, -51 - index)
                if pointer == 0:
                    raise PatchError(f"{path} contains a null data-block pointer")
                data_blocks.append(pointer)

        add_pointers(header)
        extension = _get_long(header, -2)
        seen = {location.block_number}
        while extension:
            if extension in seen:
                raise PatchError(f"{path} has a cyclic extension chain")
            seen.add(extension)
            block = self._read_block(extension)
            self._validate_block(block, T_LIST, ST_FILE, f"{path} extension")
            if _get_long(block, 1) != extension:
                raise PatchError(f"{path} extension has the wrong own-key")
            if _get_long(block, -3) != location.block_number:
                raise PatchError(f"{path} extension has the wrong parent")
            extension_blocks.append(extension)
            add_pointers(block)
            extension = _get_long(block, -2)

        byte_size = _get_long(header, -47)
        expected_blocks = (byte_size + OFS_DATA_SIZE - 1) // OFS_DATA_SIZE
        if len(data_blocks) != expected_blocks:
            raise PatchError(f"{path} has an inconsistent data-block count")

        contents = bytearray()
        for index, number in enumerate(data_blocks):
            block = self._read_block(number)
            self._validate_block(block, T_DATA, None, f"{path} data")
            # The supported original ADF contains a stale hdr_key in this
            # file's OFS data blocks.  AmigaDOS follows the header's pointer
            # table and the next-data chain, so validate those authoritative
            # links instead.  Newly written blocks receive the correct key.
            if _get_long(block, 2) != index + 1:
                raise PatchError(f"{path} data block has the wrong sequence number")
            expected_next = data_blocks[index + 1] if index + 1 < len(data_blocks) else 0
            if _get_long(block, 4) != expected_next:
                raise PatchError(f"{path} data chain is inconsistent")
            size = _get_long(block, 3)
            if size > OFS_DATA_SIZE:
                raise PatchError(f"{path} data block is too large")
            contents += block[24 : 24 + size]

        if len(contents) != byte_size:
            raise PatchError(f"{path} byte size does not match its data blocks")
        return FileRecord(
            location,
            bytes(contents),
            tuple(data_blocks),
            tuple(extension_blocks),
        )

    def _bitmap_position(self, number: int) -> tuple[int, int]:
        if not RESERVED_BLOCKS <= number < ADF_BLOCKS:
            raise PatchError(f"invalid allocatable OFS block: {number}")
        relative = number - RESERVED_BLOCKS
        return relative // 32, relative % 32

    def _is_free(self, number: int) -> bool:
        long_index, bit_index = self._bitmap_position(number)
        value = _get_long(self.bitmap, 1 + long_index)
        return bool(value & (1 << bit_index))

    def _set_free(self, number: int, is_free: bool) -> None:
        long_index, bit_index = self._bitmap_position(number)
        value = _get_long(self.bitmap, 1 + long_index)
        mask = 1 << bit_index
        if is_free:
            value |= mask
        else:
            value &= ~mask
        _put_long(self.bitmap, 1 + long_index, value)

    def _allocate(self, count: int) -> list[int]:
        result: list[int] = []
        bitmap_longs = ((ADF_BLOCKS - RESERVED_BLOCKS) + 31) // 32
        start_long = (ROOT_BLOCK - RESERVED_BLOCKS) // 32
        for step in range(bitmap_longs):
            long_index = (start_long + step) % bitmap_longs
            base = RESERVED_BLOCKS + long_index * 32
            limit = min(32, ADF_BLOCKS - base)
            for bit_index in range(limit):
                number = base + bit_index
                if self._is_free(number):
                    self._set_free(number, False)
                    result.append(number)
                    if len(result) == count:
                        return result
        raise PatchError(f"not enough free blocks in source ADF (need {count})")

    def _update_parent_and_disk_time(self, parent_number: int) -> None:
        parent = self._read_block(parent_number)
        _put_timestamp(parent, -23)
        self._write_standard_block(parent_number, parent)
        root = self._read_block(ROOT_BLOCK)
        _put_timestamp(root, -10)
        self._write_standard_block(ROOT_BLOCK, root)

    def delete_file(self, path: str) -> FileRecord:
        record = self.read_file(path)
        location = record.location
        header = self._read_block(location.block_number)
        next_entry = _get_long(header, -4)

        if location.previous_number is None:
            parent = self._read_block(location.parent_number)
            _put_long(parent, 6 + location.hash_index, next_entry)
            self._write_standard_block(location.parent_number, parent)
        else:
            previous = self._read_block(location.previous_number)
            _put_long(previous, -4, next_entry)
            self._write_standard_block(location.previous_number, previous)

        for number in record.all_blocks:
            if self._is_free(number):
                raise PatchError(f"{path} references an already-free OFS block")
            self._set_free(number, True)
        self._update_parent_and_disk_time(location.parent_number)
        return record

    def create_file(self, parent_number: int, name: bytes, contents: bytes) -> None:
        try:
            self.find_entry(parent_number, name)
        except PatchError as error:
            if not str(error).startswith("required file or directory not found:"):
                raise
        else:
            display_name = name.decode("ascii", errors="replace")
            raise PatchError(f"OFS entry already exists: {display_name}")

        data_count = (len(contents) + OFS_DATA_SIZE - 1) // OFS_DATA_SIZE
        extension_count = max(
            0,
            (data_count - POINTERS_PER_BLOCK + POINTERS_PER_BLOCK - 1)
            // POINTERS_PER_BLOCK,
        )
        allocated = self._allocate(1 + extension_count + data_count)
        header_number = allocated[0]
        extension_numbers = allocated[1 : 1 + extension_count]
        data_numbers = allocated[1 + extension_count :]

        parent = self._read_block(parent_number)
        self._directory_hash_size(parent_number, parent)
        hash_index = _name_hash(name)
        old_hash_head = _get_long(parent, 6 + hash_index)

        header_pointers = data_numbers[:POINTERS_PER_BLOCK]
        header = bytearray(BLOCK_SIZE)
        _put_long(header, 0, T_HEADER)
        _put_long(header, 1, header_number)
        _put_long(header, 2, len(header_pointers))
        _put_long(header, 4, data_numbers[0] if data_numbers else 0)
        for index, number in enumerate(header_pointers):
            _put_long(header, -51 - index, number)
        _put_long(header, -48, 0)
        _put_long(header, -47, len(contents))
        _put_timestamp(header, -23)
        _put_bstr(header, -20, name, 30)
        _put_long(header, -4, old_hash_head)
        _put_long(header, -3, parent_number)
        _put_long(header, -2, extension_numbers[0] if extension_numbers else 0)
        _put_long(header, -1, ST_FILE)
        self._write_standard_block(header_number, header)

        pointer_offset = POINTERS_PER_BLOCK
        for index, number in enumerate(extension_numbers):
            pointers = data_numbers[
                pointer_offset : pointer_offset + POINTERS_PER_BLOCK
            ]
            next_extension = (
                extension_numbers[index + 1]
                if index + 1 < len(extension_numbers)
                else 0
            )
            block = bytearray(BLOCK_SIZE)
            _put_long(block, 0, T_LIST)
            _put_long(block, 1, number)
            _put_long(block, 2, len(pointers))
            for pointer_index, pointer in enumerate(pointers):
                _put_long(block, -51 - pointer_index, pointer)
            _put_long(block, -3, header_number)
            _put_long(block, -2, next_extension)
            _put_long(block, -1, ST_FILE)
            self._write_standard_block(number, block)
            pointer_offset += POINTERS_PER_BLOCK

        for index, number in enumerate(data_numbers):
            start = index * OFS_DATA_SIZE
            chunk = contents[start : start + OFS_DATA_SIZE]
            next_data = data_numbers[index + 1] if index + 1 < data_count else 0
            block = bytearray(BLOCK_SIZE)
            _put_long(block, 0, T_DATA)
            _put_long(block, 1, header_number)
            _put_long(block, 2, index + 1)
            _put_long(block, 3, len(chunk))
            _put_long(block, 4, next_data)
            block[24 : 24 + len(chunk)] = chunk
            self._write_standard_block(number, block)

        _put_long(parent, 6 + hash_index, header_number)
        _put_timestamp(parent, -23)
        self._write_standard_block(parent_number, parent)
        root = self._read_block(ROOT_BLOCK)
        _put_timestamp(root, -10)
        self._write_standard_block(ROOT_BLOCK, root)

    def finish(self) -> bytes:
        _set_checksum(self.bitmap, 0)
        self._write_block(self.bitmap_block_number, self.bitmap)
        # amitools writes the root block whenever it flushes a dirty bitmap.
        # Normalize the BSTR padding as amitools does, then recalculate it as
        # the final reproducible filesystem operation.
        root = self._read_block(ROOT_BLOCK)
        root_name = _get_bstr(root, -20, 30)
        _put_bstr(root, -20, root_name, 30)
        _set_checksum(root)
        self._write_block(ROOT_BLOCK, root)
        return bytes(self.image)


# Standard-library HUNK packer, mirrored in src/zlib_hunk.py.
LOADER = bytes.fromhex(
    "598f48e7fffe47fa048c2f6b0018003c2c780004201372014eaeff3a4a80670000922840222b001041f31800202b0004"
    "6100008ab0ab0008666c222b00104bf3180061000408204c20136170b0ab000c665445eb00182e2b00142007e5884bf2"
    "0800204c225a201d670622d8538066fa226afffc241d6714201d221d4deb001822361800d3b10800538266ec538766d4"
    "2c780004224c20134eaeff2e4eaefd844cdf7fff4e752c780004224c20134eaeff2e4cdf7fff588f70144e7572017400"
    "4a80672876001618d283b2bc0000fff1650692bc0000fff1d481b4bc0000fff1650694bc0000fff1538066d848423401"
    "20024e75ff5b006c0336dbb66ddbb66ddbb6cddbb66ddbb66ddba86dce8b6d3b48e7ff00720874002f0251c9fffc5340"
    "32002448141ad4025277200051c9fff6244f720f74003e82d452d44234c251c9fff83200787f24487a001a1a67745345"
    "3c05dc4636376000527760003c057400e24be35251cefffa1602d6433c009c41bc6f002a6302e54eba3c0008641ee74e"
    "8c05740054050bc23e024447ce7c01ff864733863000964264f86026e04a510547f130003e13660a52443e0408c7000f"
    "3687e20adf47de4747f1700051cdffe6368651c9ff844fef00244cdf00ff4e757000bc01640a101deda88a80500660f0"
    "03c05340c045e2ad9c014e75e64e9ac67a007c00721061d8544d600218dd51c8fffc4e7548e706047a007c004bfafee6"
    "303c027d6004303c028072002f0151c8fffc720561aad07c01013f00720561a052403f0072046198564043fa01fd41ef"
    "0004740036007203618614191180200051cbfff443ef01447013727f6100feb2342f0002d45753422448204970007207"
    "bc01620a101ded688a40500670001005d040303000006a1ae04d5106530664041a1d7c07e24dd140d040303000006bec"
    "600ac2005201e26d9c01e648b03c00106532671ab03c0011670a72076100ff125040600672036100ff087200600a7202"
    "6100fefe122affff5440944014c151c8fffc600214c051caff847000323c008920c051c9fffc41ef0004302f0002323c"
    "010038016100fe0ad0c043ef07a0301772006100fdfc4aaf0a0467064cef206009fc41ef014470007207bc01620a101d"
    "ed688a40500670001005d040303000006a1ae04d5106530664041a1d7c07e24dd140d040303000006bec600ac2005201"
    "e26d9c01e648b044640a18c060b84fef0a084e7567f845ef0684d4c0321a7000bc01640a101deda88a80500660f003c0"
    "5340c045e2ad9c01d052360041ef07a070007207bc01620a101ded688a40500670001005d040303000006a1ae04d5106"
    "530664041a1d7c07e24dd140d040303000006bec600ac2005201e26d9c01e64845ef0a10d4c0321a7000bc01640a101d"
    "eda88a80500660f003c05340c045e2ad9c01d052204c90c0e24b6504534318d818d851cbfffa6000ff0a205f3600e86b"
    "534364027600720007c194413f023f0351c8ffea4ed000182a10111200080709060a050b040c030d020e010f48e7fefc"
    "243c000001022f025242701b780261ba343c8001701d780161b07a007c0072036100fd5e2f00e208103b00bc41fafd6e"
    "4eb00000201fe20864e44fef00ec4cdf3f7f4e75"
)


def longs(*values):
    return struct.pack('>' + 'I' * len(values), *values)


@dataclass
class Hunk:
    allocation: int
    kind: int
    size: int
    data: bytes
    relocations: list


def parse(data):
    pos = 0

    def word():
        nonlocal pos
        if pos + 4 > len(data):
            raise ValueError('Truncated HUNK file')
        value = struct.unpack_from('>I', data, pos)[0]
        pos += 4
        return value

    if word() != 1011 or word() != 0:
        raise ValueError('Expected HUNK_HEADER without resident libraries')
    count, first, last = word(), word(), word()
    if not 1 <= count <= 1024 or first != 0 or last != count - 1:
        raise ValueError('Unsupported HUNK table')
    allocations = [word() for _ in range(count)]
    if any(a >> 30 == 3 for a in allocations):
        raise ValueError('Extended allocation flags are unsupported')
    hunks = []
    for allocation in allocations:
        kind, size = word() & 0x3fffffff, word()
        if kind not in (1001, 1002, 1003):
            raise ValueError('Unsupported HUNK type')
        if size > allocation & 0x3fffffff:
            raise ValueError('HUNK exceeds allocation')
        length = 0 if kind == 1003 else size * 4
        if pos + length > len(data):
            raise ValueError('Truncated HUNK contents')
        contents = data[pos:pos + length]
        pos += length
        relocations = []
        while True:
            tag = word()
            if tag == 1010:
                break
            if tag in (1004, 1015, 1020):
                short = tag != 1004

                def relocation_word():
                    nonlocal pos
                    if not short:
                        return word()
                    if pos + 2 > len(data):
                        raise ValueError('Truncated short relocation')
                    value = struct.unpack_from('>H', data, pos)[0]
                    pos += 2
                    return value

                while True:
                    n = relocation_word()
                    if not n:
                        break
                    target = relocation_word()
                    if target >= count or n > len(data) // 2:
                        raise ValueError('Invalid relocation target/count')
                    for _ in range(n):
                        offset = relocation_word()
                        if offset & 1 or offset + 4 > length:
                            raise ValueError('Invalid relocation offset')
                        relocations.append((offset, target))
                if short:
                    pos = (pos + 3) & ~3
            elif tag == 1008:  # Symbols do not participate in loading.
                while True:
                    n = word()
                    if not n:
                        break
                    pos += n * 4
                    word()  # symbol value, with bounds check
            elif tag == 1009:  # Debug information, not loaded into the HUNK.
                n = word()
                pos += n * 4
                if pos > len(data):
                    raise ValueError('Truncated debug record')
            else:
                raise ValueError(f'Unsupported HUNK record {tag}')
        if len({off for off, _ in relocations}) != len(relocations):
            raise ValueError('Duplicate relocation')
        hunks.append(Hunk(allocation, kind, size, contents, relocations))
    if pos != len(data):
        raise ValueError('Trailing HUNK data')
    if hunks[0].kind != 1001 or len(hunks[0].data) < 8:
        raise ValueError('First HUNK must contain an executable entry')
    return hunks


def pack_hunk(data):
    hunks = parse(data)
    flat = b''.join(h.data for h in hunks)
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed = compressor.compress(flat) + compressor.flush()
    if zlib.decompress(compressed, -15) != flat:
        raise ValueError('DEFLATE round-trip failed')
    descriptors = b''.join(
        longs(len(h.data) // 4, len(h.relocations)) +
        b''.join(longs(offset, target * 4) for offset, target in h.relocations)
        for h in hunks)
    offset = 24 + len(hunks) * 4 + len(descriptors)
    metadata = longs(len(flat), len(compressed), zlib.adler32(compressed),
                     zlib.adler32(flat), offset, len(hunks))
    code = LOADER + metadata + bytes(len(hunks) * 4) + descriptors + compressed
    # Inflate may read a lookahead word beyond the DEFLATE end.
    code += bytes(4 + (-len(code) % 4))
    result = longs(1011, 0, len(hunks) + 1, 0, len(hunks))
    result += longs(*(h.allocation for h in hunks), len(code) // 4)
    # DOS loads an entry JMP in original HUNK 0, the others start zeroed.
    result += longs(1001, 2) + bytes.fromhex('4ef9000000004e71')
    result += longs(1004, 1, len(hunks), 2, 0, 1010)
    for h in hunks[1:]:
        result += longs(1003, h.allocation & 0x3fffffff, 1010)
    result += longs(1001, len(code) // 4) + code + longs(1004)
    for index in range(len(hunks)):
        result += longs(1, index, len(LOADER) + 24 + index * 4)
    result += longs(0, 1010)
    parsed = parse(result)
    if [h.allocation for h in parsed[:-1]] != [h.allocation for h in hunks]:
        raise ValueError('Original allocation table changed')
    return result


def compress_program(program: bytes) -> bytes:
    try:
        packed = pack_hunk(program)
    except (ValueError, zlib.error) as error:
        raise PatchError(f"zlib packing failed: {error}") from error
    if len(packed) != 150108 or sha256(packed) != PACKED_PROGRAM_SHA256:
        raise PatchError("packed executable does not match release 1.8.1 "
                         f"(zlib {zlib.ZLIB_RUNTIME_VERSION})")
    return packed


def build_patched_adf(source: bytes) -> bytes:
    if len(source) != ADF_SIZE or sha256(source) != SOURCE_ADF_SHA256:
        actual = sha256(source)
        raise PatchError(
            "unsupported Disk 1 image: expected SHA-256 "
            f"{SOURCE_ADF_SHA256}, got {actual}"
        )

    ofs = OFSImage(source)
    original_program = ofs.delete_file("STREET_ROD")
    patched_program = compress_program(patch_program(original_program.data))
    ofs.create_file(ROOT_BLOCK, b"STREET_ROD", patched_program)

    original_startup = ofs.delete_file("s/startup-sequence")
    if sha256(original_startup.data) != (
        "ea12869fb12ec9175f235d658150ee92d426f431e0f1d04103bd3e93e329fe65"
    ):
        raise PatchError("startup-sequence does not match the supported original")
    startup_directory = ofs.find_path("s").block_number
    ofs.create_file(startup_directory, b"startup-sequence", STARTUP_SEQUENCE)

    if len(SPLASH) != 106620 or sha256(SPLASH) != SPLASH_SHA256:
        raise PatchError("internal splash verification failed")
    ofs.create_file(ROOT_BLOCK, b"SR2_SPLASH", SPLASH)

    trainer = ofs.read_file("StreetRodA.sav")
    if len(trainer.data) != 304 or sha256(trainer.data) != TRAINER_SHA256:
        raise PatchError("trainer save changed unexpectedly")

    result = ofs.finish()
    actual_result_hash = sha256(result)
    if actual_result_hash != PATCHED_ADF_SHA256:
        raise PatchError(
            "internal patched ADF verification failed: expected SHA-256 "
            f"{PATCHED_ADF_SHA256}, got {actual_result_hash}"
        )

    # Verify the logical files from the completed image as well as its hash.
    check = OFSImage(result)
    if check.read_file("STREET_ROD").data != patched_program:
        raise PatchError("patched STREET_ROD read-back verification failed")
    if check.read_file("s/startup-sequence").data != STARTUP_SEQUENCE:
        raise PatchError("startup-sequence read-back verification failed")
    if check.read_file("SR2_SPLASH").data != SPLASH:
        raise PatchError("splash read-back verification failed")
    return result


def default_output_path(source: Path) -> Path:
    return source.with_name("StreetRod2-KS31-AGA-060-Disk1.adf")


def write_atomic(path: Path, data: bytes, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise PatchError(f"output already exists: {path} (use --force to replace it)")

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", dir=path.parent, delete=False
        ) as handle:
            temporary_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Patch an original Street Rod 2 Amiga Disk 1 ADF for "
            f"Kickstart 3.1, PAL AGA and an MC68060 (version {VERSION})."
        )
    )
    parser.add_argument("source", type=Path, help="original Disk 1 ADF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output ADF (default: StreetRod2-KS31-AGA-060-Disk1.adf beside source)",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="replace an existing output file"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.source.expanduser().resolve()
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else default_output_path(source)
    )

    try:
        if source == output:
            raise PatchError("source and output paths must be different")
        try:
            source_data = source.read_bytes()
        except OSError as error:
            raise PatchError(f"cannot read source ADF {source}: {error}") from error

        result = build_patched_adf(source_data)
        write_atomic(output, result, args.force)
    except PatchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"error: cannot write output ADF {output}: {error}", file=sys.stderr)
        return 1

    print(f"Source verified: {source}")
    print(f"Patched ADF:     {output}")
    print(f"SHA-256:         {PATCHED_ADF_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
