# -*- coding: utf-8 -*-
"""Filenor simgesi (128 px PNG, gomulu). Sistem simgeleri ISO derlenirken kurulur;
depodan ya da simge kurulmadan calisirken pencere simgesi buradan uretilir.
GTK'siz."""

import base64
import os

PNG_128 = (
    "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAABmJLR0QA/wD/AP+gvaeTAAAZ/UlEQVR4nO2de5Rc"
    "VZ3vP3ufc+pU9SP9SrrTedgxBDqkIUBCBIIgBBDBxzAKiFdQhsE1joMzMqO4vDpXx/EuF7i8jDrR6xIZrsMMiozO"
    "ZdCAEsAAeklIiAToPDov8ug8+pFOP+p1ztn3j+qqrsepqnOqqjvdSX3Xykqf/fjtXefzq3328xRUVVVVVVVVVVVn"
    "osTkF3GVvvT82CoBV9oOS6VQ5wjEfBANClULGCjlmtM9tHCMe3SR9MVUNLvP+md8XhFBqpNKqZMosVvibFNCviqV"
    "eHb79o39/ivrT5PiAF1dXQG05g9Ztn2HRKyxlV1n2za27aCUg+MolEr8O1XwPdufVPgJCSEQQqBJiZASTZMYhm4p"
    "R/wBnCeUrT/S0/PKyWI1KUUVdYCzlq9uDdj8LUJ8yrKt5njcwrKsBGg3VeEXlK5LDMPA0I2TwE+cgHZ/z+uvHPRl"
    "pIgq4gCdnZfXC0N9VcBfxuLxmlgsjuM4hTNV4Xu2L2XCEQKmMSaleBDLvH/HjpeHfRp0VdkOsHT5FR/Bsf/JsqwF"
    "0WisOHiowi8q9/RCSgKBAIahvy2lvGvnW5vW+zSca7PUjIsWLQqadfPW4qi7ItEIlmV7y1iFX559BbquEQwGHSn4"
    "7q4ds74AL1g+C0mpJAfo6nr3O2zhPGVZ1vmRSDT/Mz5bVfjl2U+LFkIQDJrouv68qQdufvPNPwz4LCxhx2+GJV2X"
    "LDOE/nQkGl0Yi8W8Z6zCL89+ns9rmiamafToQl3b3f3afp+F+nOAJV2XLNPRfxeJRmbH43HvGavwy7Nf5PMahkEo"
    "ZO6TSl+zY8fGvX5K9uwA483+y5FIdEEV/vSBn5RhGARD5n5NhVbv2PHyYa+lSy+JFi1aFLSF81Q0GqvCL5TtFMEH"
    "iMfjRCOxDpvIk8uXL6/1WgNPDmDWzVtrWdb51Wf+9ISfVCwWIx6PrxyLGo94rYVWLEHX8itudmznm+FwxKvNKvyi"
    "qjz8pCzLwjD0ZS1z5h8b6O99tVj6gn2A8Rm+t8Lh8ILqOD9f8ukDPykpBbW1tWHhsHLXri3dBdMWihSG+qplWVX4"
    "eZNPP/igcByHSCQSUlL9oFjqvI+As5avbtUVj4bDEcPTRE8Vfnn2KwQ/KcdxMHR9Ucuc+T0D/b3b8uXI2wIEbP4u"
    "Fo/XVOf23SKmN/zkZWKWlm92dXUF8uVydYCurq4AQtwdi3kY8lXhl2d/kuADWLaNbVsLI7Z5Z76crg6gZNOfWLbV"
    "XF3SzY6YOfCTodFoDOGoL5Cnw6+7BdqOc3s8XmSBKc/NEIEgel0zQmabnjz4TnQUa7jPV3FnAnwA27axHWfJWZ0r"
    "rt69Y8tz2RZcHOAqXRK72rIKOIDLzdAb2qhduppAy0KUKHebgf+bETm0neGtz6CUU4WfpVgsTigk/xwo7gBLz4u+"
    "y3ZUvZ9tXOa8TuoveC9IWdJHySqgpFzB+UsRUnBy89MoCj26ziz4AJYVB2XeCFfp2XsHchxACHGFbef59uf55ifh"
    "ly/vN0OadZht78wJQ8HJLU8nWgKP9k9n+KBQCmzHbjz73KHVu7rZkB6bQ812WGrbLjcvz82oXbp6yuEXktneyawV"
    "70OI7DqdmfCTsiwbZXNVdoqcFkAK1Znz7SnQ4Qu0LMyogBMeZnT7SzixcN5qVaK3rzfOZdaF16PXNaPVNGTEJpwg"
    "vSU4s+EDOI6NQpyXnSr3EYCY7zhpmQsM9bTappwO3+j2F4kc3pm3WpUa6imlcCIjxCKjBGYrtJrGjFQTTrDOdcva"
    "mQQfIMFULcsOd2m7xUQHsMg4X8jcmWQ7Opa3WpMyzleKWN9B7NETOanN9nOYteLGnHqeafAhMTUsJLOzw3McQKFq"
    "SzuxU0STAT/1tyLWf5Do0T05Ccz2s5l10Q0pJzgT4QPjp7BozA53670FZhT8VJhipPtFIoe25yRIOgEuLVYyrz/N"
    "LPhpMrMDch1gJsJPxSlObn163Akyld0SpOfxpxkL31Wexm8lFzyV8JMJlMPJrc+4OkEw2wnOcPjgwQFmFPzUnx6c"
    "IGeewId9t9CZAN9tIs9HdbwXfIrgGw2tiLRhafhgN3p9C4HWzBnDmndeBApOvvZrlONlt9PpCR8KOMBMgw9Qt+zK"
    "3Ggh0Oubc+YJnMgIqPcytGWdZ/uuoTMYPuTbD1Cpgqey2c+bRBHrO4A9ljtPEJx/Lnp9ztC4qP3TBT64zgNUqOBJ"
    "hq+iIz6qoogdP+A6WSQCIW/1yQ49DeBDkT5AyQVPwTffGhkgfOANQgtzpreRwbrEGkGwDhEIIXUjkUsppBFE2XG0"
    "YB12JJ8TnRnwwZMDlDfMKG6l9GZ/+I+/Jbx7CzJYi1bbSP15V1PXubpIs55QfddVONExlG0x8OK/YQ0n38d0+sJ3"
    "Cy3iANO3w5eUY8dovuTjNFx0I0IzihnIkDRraHrXTTSufD8nXv0Vfc//ONE5zFfqaQYfCjrA9Idf23kZcz/4ebTa"
    "nCnuRA47TnzgEE40caxNmiGM5nk5jiI0g6ZLbmLWee/h8BPfYGzvltxST0P4kNcBpj/8lqvvpOWK2yFrOTo+cIiT"
    "29YT7tlE9OheyN7bICRm22JqzlpF/QXXYDTNS0VptU0suOMBjj29lhMbf3nawwdXB5j+8Ftv/CyNq27KCIsP9tL/"
    "3MOM7vhDLvQMcw7RIz1Ej/Qw+PufUdd5Gc1r7sJoagcSS9xtN/41RlM7x575/mkNHzyPAnxYLJisMt/8DPhKMbT5"
    "KfrXP4SyfLy7AEA5jGx/mdGejcx53z3UX3BdKqr5sluIDfRyYuMv/VTYrRDXy+kAHzwuBrlbnPpvft05lyWa/WQK"
    "x+HYr79D3zM/8AS/tXU2D377H3nw2//I3LmtE3asOMeeepC+Zx9CpR2GabvhM4lpY28VLv4ZTjn83BhvDlB2M1g+"
    "fBmqp+1Dn5945ivF8XXfZXjrbzzX4ktf/Btu/vAHuPnDH+CJn/6Yee1zM+KHXvkF/c89nLoWUmfeR76MDOQso3vQ"
    "9IcPXhxgGsAHmL3mzzJ6+0Ov/pcv+Nnq6FjA44/9yNUJhl//bepar2+h+dJbfVqfGfChmANME/haXQsNF96Quk50"
    "+H7ssy7wwLf+mf37J161m88Jjq9bi3XyeOq6+YqPodc1eyxl5sCHQp3ASYJvNM2l5qyVSCPfHHxuttolqxD6xAnn"
    "/uce9t/hA3qPHOWW2+7m8Z/+iEUdC4GEE/zHzx/mltvu5uDBxMu1lBVj4MV/o/X9nwNABkI0rvoQfc8/4qG2uZfT"
    "FT7kc4BJ7PDVLPYHHyA475xUWHzwcGKoN67W1tl86Yt/Q1vbHE82ASKRzPcdLZjfzk8f/SG33HY3vUeOAjDy+rM0"
    "rf5oang464LrijjAzIMPbg4wyb199yNb+a3otY1owfpU+PAf12eM85Mdu3LV0bGA+75wD/f+3d8nyncchretp/nK"
    "xKgj0DSfQMsCYv1ub2ufmfChaCewvDGmW8Kxnk3Y0VHP2YzG9sz8uzd5Lb1sjfVklhXqWO6SaubChxLWAsqBD2Cd"
    "7OPklnWe7RvXf2YizooTO7YnI/6b938HwNcjYM7sZpZ2np0Rtn//QR741j9nhMWO7kbZ8dTagdm6qHBtpzt8l2hf"
    "awHlwi/FvtEwMWFjDfZmTNQAHDvWl2q2k6ppms2KjyUcZ/NjawkPTvz0zrz2uTz+2I8y0h881Mttt/9F6vmfqo/j"
    "ED9xlEDLAgAWX/ffuOaOu1NHzRQTjBL/J07iJj/HRJxiPDorThEbHWFsoJeRw3s4+MpvOLbt9yg7PiXwwcdawKmA"
    "D2R0GIs9OgBqW9p43/9YS33b/FTYS9//OgDtc9t4/LEf0dGxIBW3f/9Bbv3Ypzjce8TVnhOeWB62HSoKXynQa+qY"
    "FTqb+vln077qeiJDfXT//Lsc+n+/znGCSsOHSp8LqDB8v/v23eCn674v3OMLft5qURn4uXGKwKwWLrjrH3jXvWsx"
    "aidOPU8GfKjkuYBJgm/HJw6bamb+dyC7wR8+eogtj33fNb1X+DJUN1G+nFz46WEtS9/Fpfc9RLCprYLwc9NX5lzA"
    "JH7zrRPHUn/rTe0IKXP6AW7wR/qO8Mw3PsvY4MTLo5IdRoD7v/U9jhw5RiEJKTEa21LXAV1OCfzk/7Xt7+Tie9fy"
    "h2/eiRXO3qlUPnyoxLkAn/CNpnZqzlqBMGo8pddnTezvE7pBoG0x0d6eVFhtc6trsx8Pj7D6L76UY33dYOL/5Xd/"
    "hfRB3dhAX06HMdC2JGP3UMBINJhTAT8ZV9PWwXmf+Hu2/vCLee9RjjzChzwOMJnf/JrFKxF5ZwJz08dP9GbmP2tV"
    "hgNcdNunXZ/5TQuX0LSwWP1ylewwAtQsWZURVxvUphR+Mqz1ojXMueA9HP/j76gkfPCzH6BSzb7KdxTLPb01egI7"
    "PPGjmfXLrwHf5/pKkJDUn78mdRkwJAFdMtXwk/+f/af3IDS/83ZFIZV4LqCMZ/5ozyZql6xKvNHLo8FI705qF18M"
    "gNE0j7rOyxjZ/jIAr/30f9PWuTynFRg80EN4aLBYRVNKPgKSqjv33al1AIDGWoNTBV8BNa0dNJ1zMQPdr7h/gBLg"
    "QynnAsqAD4mZwIzzeB6GesPbnmPx5/499TxuXnMXoz2bUFaM0YFjPP0Pn+H6r65lVtvEEM8I1bH+gfsYOd6bz2xe"
    "CT1Ay5o/m7gWguZZ+imDn5x7aF1xrbsDeITvFuqvTSkTfm6ENy+1hvs58eqvUtdGUztzbvir1PXowDGe+fo9DB89"
    "lAqrmz2X67/yPWqaih8SydacG+5Bb5jo/TfP0tGlOKXwFdDQ0ZVb2TLgQ0EHmB7wk+p7/sfYoxNNev3y62i45MOp"
    "69H+ozz99b/KcIL6tvmpKWGvarj0w9QvvzZ1rWuCtgbzlMNHgdmcuTBWLnzI6wDTCz4kXgnX+x/fyDjP37LmrqJO"
    "4EeNl36ElqvvSl0LAQvnBFN9zlMJXwFaMK3fVAH4UNKewDILLgF+UqN7tnD8mYkVOyEls6+9m9YP3oswEhs3R/uP"
    "su5rn6Znwzp6NqzL6Njlk9ADtH7wb2m55s8RaW89bW8yqQlqGdU+VfCTZWTdkpx7VDw0U4U7gdMIflKDr/wneuM8"
    "mi+7JRVWv/w6Qu9cwcCGf2Xk9WcZG+zLGM/nlZDUnvtuZl99J3pj5r7A2Q0GTbMSnc5lLTq3LjVBwfNvx9hwIEY8"
    "5RCJek4FfKXcbknp8MHXnsAyC64A/GTosWe+T6z/MG033pN64ZNe30Lr+z9H0+qPMrxtPWM9mxLr+VnTxkJKAm1L"
    "qFmyivrz12QM9SDR7Lc3mzTVJ4+Uw62dJg2BxHb0m842uWJhgP/qibK5N86Uwvdxj9yVG+NxT6DvBFnJKwc/+ceJ"
    "Tf9JrG8/8z7yZfT6llQao6md5itvp/nK21F2HGugFzuWWFCSZi2BpnbQ3D+2rgkWzgnmNPsNZgK+LgW2gpYg3Hle"
    "kDXvMPjFjig7B60pgZ95V8qHD572BPpOkJW88vCTGtv7Gnu++3GaL72V5ss/igxmrhYKzcCY8w6KHRqXUtBcp9Pa"
    "aLp2+FLpROKfowS2o3jHLI3Praph61GLX+6McGzMmVz4bjfB7R75iPF3NnAawU8GOLEIfRt+wuDmJ2ladROzLryO"
    "QJP7foBsBQxJY61ByywdrdA4P0tSgNQSrYHtKC5s0zm/tY7fH4zxf3dFGI66dRTLh5+WMkelwAdfDjD94KfLHj1B"
    "3wuP0PfCIwRaFhDqWI45p4Oz3vtxrPE3xmtaYkk3YEhqg5rnuf1sOSrhBFrSEZxEwisWBljZbvDrnijP7YumdRQr"
    "Az/fr7h4hu+SsKx3BOUteIrhZyvWfzC1ffuaT3wq40ZPAE6EeJ3eTZflKIQATQikAF2CUokWoUaHm5cGWbPI5Fc9"
    "ETa8HZ228MHTauDMgp9bncrCJy295SgsJ2FHjDuCLgVCQHNQcMd5Ib58eT2dzXpF4Gff2nLhw2SfCyiqyYWfnqtU"
    "+MX82VEQdxS2k8grBRhSoMvEyGFRg8Z9l9Xx+UvqmFevTSv44GctwJs9H5oK+KoC8L2VayuI2wp7PLkUYGgCbdwR"
    "ls3R+dqV9dx5QQ31pigJfqpeBT5voUs3eVsLyBfq8p7dQhs3PduvEHwoH77fJ5rtKOK2wlGJn+rUxh1BCoEu4T0d"
    "JvevaeDCuYZv+Ol1z/d5813mU1nnAuzRAVIPwHHVLbsShMCJ5fvpmKmDn7oqA36ppSc7iroQqf6BUgJLKUKG4JPL"
    "a9jSe8IX/Py1KQ0+eBwF5LPnRMPEjr9NoLUjFaaF6mhYcUOeHEXsV+iZn2GhXPhlVkGR50d7wTd8T9PBPutb+rmA"
    "8doMb38xZ77djyYTftJOOfBLqYUgMRowZGKYmGgRIOYkHg1jccW/bB0brx1TCD83QWnnAtJqYw0dY2jLOhpW3JCx"
    "lOpFkw+fKYevSYGWfI0R4Dhgj5dnO7Dh7ShPvBXmZNTxDT/TCcqHD6WcC3BxxWjvDgZeGqB+6RUE5nTkvLyxoP1J"
    "hJ9urVT4eX9DOUuaSKwpJD95cpo4mfvN4xaPvj7KwZP2RL18wp+oSWXgg99zAQVuhjV0nMFXfoEwTPS6FoRu5LVU"
    "WfjuNyMVevPHyoJfrEZyfEYw6fPOOPjkQ3HvCZvH3hhje1+85Gf+ZMEHFwcoBX5GsniU+ODhvJamFD7lffNVtrE0"
    "pU8FJ21ZKvGMBxgIOzy5M8Lz+6IJWxWAn9MalQkfvK4F+B0MTxP4qagy4LvZ02UaeBLPdmc8TziueHJnhN/uiRCz"
    "J8pI1W0awQcvDnCmw3cxmuzZZ3fwXjwQ5RfdYYaiKhdmms1S4adQlAjf1ZkL25nZ8FPhZcB3s5vs4CXtb+6N8/O3"
    "whwZsd1hptmaTvCh4J7AmQ8/edcrBT/ZwUuG7z1h87M3x+jun9gSNpnwiyPxBx/y7gk8TeBD2fCVUgxGFE1BgTX+"
    "rT8+5vBEd5iNh2I4aeknG37hu+YfPrjuCTx94KeuyoCvgH/dNsYd5yfeZ/CbPRGe3RMh7mQDnigjVYNKw8/LpjT4"
    "4HtPoM+CTwP4KNh6NM7WI0OZMNPSTxV8P5i93ukyDtpPf/jJsHLgu8LMCJsoIzdumsF3aUHcHCCaL7/ngqcNfIiN"
    "jpw28K1w+mvySoKfwzbXAQQnRcG5/JkDHyA8ePS0gK8UxE4mX3jlH/4405zfxMv96VjlHJd5V/VmFnyAE3veOC3g"
    "KyDWfyjv5y3yzU84gPLgACC7pWsLMPPgAxza9Gwi5QyHj4Kh7hf93YW0Z76UEgcOZCfJcQCBvU1qmqcipjt8gP7t"
    "Gxnu3Tfj4TtOnKHul7zfhawOn5QCIdXO7GQ5DiDRXtD1dAeYufABHNtm+xPfm9HwFYqBjU8RH8p8saVX+ABSaggl"
    "u3PCswO2b699WUo5lOg0zGz4ieSKo1tfoHfLczMWvh0e5cizD3m7Cy7wATRNQyj1u+xwlz7AC5ZS4unMVsCl4BkC"
    "P6nXH/4qw4f3jAfPHPjKcdj/s68RH5545a1f+EIINE2e2LPnzS3Zca7dfSl5KBDIPVQ9U+ED2NEwr37nswwf3jOj"
    "4B966p84mdb58wsfwDB0UKwHcg5yuDrAzu5N6zVN7tbSOoMzGX5S4cGjvPLAp+h/a+O0h2+HR9n7f+6j7+XHi9+F"
    "AvABdN1ACvmoW5x7Ow80z54flVJ8IB63Tgv4yVAnHuXwxnWMHT9I4+LlyEBoIn4awHecOAMbn2Tfo/+d8OHtxe9C"
    "EfhSSoJBs2/PbvPT0Juzfz//lN/KlcY5Y+waGQ132LZ9WsDPltQ0WrpW03bx9TQs6sJomIPQAkwlfDsSJjp0jFj/"
    "IYa2v8TQWy+W1dvPVjAYJBgM/M/du974ilt8wf3bS869+A7Htn8yOpJ9zGvmwy9q36PDe7Zf9OP4tO8BvpSSurqa"
    "kVjEWXTo0PZ+1zSFDPR0v/qoRNtgGOkdwip83/ZPAXwA0zQRQn4vH3wovhyscOy/DAbNcGJ9oArft/1TBF/XdQxd"
    "39/UYH6jULq8ncCkBgaOHG9uWTCo6+L98bjf3+utwvdZYOFsHuELIaipCSEQn3zrrT++UShtUQcAGOg/vKllzrzz"
    "pZTLLMvyVIkq/MLFTRZ8gFAohGFoP9i7583/VSyt5x1BNab1SSNgbA4EAsUTV+EX0eTBDwQC6Ia2RRK910v64qc4"
    "09TZefk8W4R/HwlHO/I/DqrwfRZYOJsv+AZB09xvxe3VBw7sOOwlj689gTt2vHxYU/rVoZC5L3NkkFQVvs8CC2fz"
    "Cd80A8eVY73PK3woYVPojh0b9+pCXRUMmbtM00yLqcL3WWDhbD6b/aBp7sexr9y3b+f24jkmVNKu4O7u1/abmnlp"
    "IBB4LhQK5b4OoAq/PPs+evuhUAgzGNhi6MblfuGDx1GAm44fPxge6O/899lt0XrDMC5xHEc4jqrC92ipEuP8mppE"
    "b18TsVt37er2/hNpafLVCcynzs6VV9vC+RcrZndEo1HsvO8MqsIvmM3j9K5pmhi6vh/FX+/d++aTRTMVUMktQLr6"
    "+3v3tbctfQgRc4yAsRJEIPFShPQPVIVfMJuHVT3TNAmFzBFd17/d3Bj8aLFJHi+qSAuQrnPOuWy+LcbuE0r7ZNyy"
    "GuLxGLZtZzlDEVXhA4lnvGHo6LqBrmt9UoofRsasBwvN7ftVxR0gqa6uq+qi8eFPKOXcIqS6PB63jYQjONj2+A8r"
    "uH3wMxC+EAIhBFJKpBRIqaFpGpomT6BYL4V8dPfuwK9gs9+5+KKaNAdI14KuruagZV6rcFYKxHJQixGiASUaQAVT"
    "Cc9I+MSUYlQphkAdQLJLKNmNozbs3fvmZly2cVVVVVVVVVVVVVWVq/8PYtTywqj3klgAAAAASUVORK5CYII="
)


def cikar(dizin=None):
    """Gomulu simgeyi onbellek klasorune yazar ve yolunu dondurur; yazilamazsa None."""
    if dizin is None:
        import filenor_sistem
        dizin = filenor_sistem.onbellek_dizini()
    yol = os.path.join(dizin, "filenor.png")
    try:
        veri = base64.b64decode(PNG_128)
        if os.path.isfile(yol) and os.path.getsize(yol) == len(veri):
            return yol
        os.makedirs(dizin, exist_ok=True)
        gecici = yol + ".%d.tmp" % os.getpid()
        with open(gecici, "wb") as f:
            f.write(veri)
        os.replace(gecici, yol)
        return yol
    except OSError:
        return None
