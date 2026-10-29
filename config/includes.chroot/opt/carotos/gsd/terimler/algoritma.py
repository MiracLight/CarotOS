# -*- coding: utf-8 -*-
"""GSD -- Algoritma ve Veri Yapıları terimleri."""

TERIMLER = [
    {
        "id": "algoritma",
        "baslik": {"tr": "Algoritma", "en": "Algorithm"},
        "kisa": {"tr": "Bir problemi çözmek için izlenen, adım adım tanımlanmış kesin yöntem.",
                 "en": "A precise, step-by-step method for solving a problem."},
        "aciklama": {
            "tr": "Bir algoritma, bir yemek tarifi gibi düşünülebilir: belirli bir girdiyle başlar, "
                  "açıkça tanımlanmış adımları izler ve her zaman bir sonuçla biter. Aynı problemi "
                  "çözen birden fazla algoritma olabilir; aralarındaki fark genellikle hız ve kullandığı "
                  "bellek miktarıdır -- bu da \"karmaşıklık\" kavramıyla ölçülür.",
            "en": "An algorithm can be thought of like a recipe: it starts with a specific input, "
                  "follows clearly defined steps, and always ends with a result. Several different "
                  "algorithms can solve the same problem; what usually separates them is speed and how "
                  "much memory they use -- measured by the idea of \"complexity\".",
        },
        "ilgili": ["karmasiklik", "veri_yapisi"],
    },
    {
        "id": "karmasiklik",
        "baslik": {"tr": "Zaman Karmaşıklığı (Big-O)", "en": "Time Complexity (Big-O)"},
        "kisa": {"tr": "Bir algoritmanın girdi büyüdükçe ne kadar yavaşlayacağını ifade eden gösterim.",
                 "en": "A notation describing how much slower an algorithm gets as its input grows."},
        "aciklama": {
            "tr": "Big-O gösterimi, kesin saniyeler yerine büyüme eğilimini anlatır: O(1) girdi "
                  "büyüklüğünden bağımsız sabit sürede çalışır, O(n) girdiyle doğru orantılı büyür, "
                  "O(n²) ise girdi iki katına çıktığında işlem sayısını dört katına çıkarır. 10 "
                  "elemanlık bir listede fark edilmeyen bir O(n²) algoritma, bir milyon elemanda sistemi "
                  "kilitleyebilir.",
            "en": "Big-O notation describes a growth trend rather than exact seconds: O(1) runs in "
                  "constant time regardless of input size, O(n) grows proportionally with the input, and "
                  "O(n²) quadruples the work when the input doubles. An O(n²) algorithm that's "
                  "unnoticeable on a list of 10 items can grind a system to a halt on a million.",
        },
        "ornek": "O(1), O(log n), O(n), O(n log n), O(n²)",
        "ilgili": ["algoritma", "hizli_siralama", "ikili_arama"],
    },
    {
        "id": "veri_yapisi",
        "baslik": {"tr": "Veri Yapısı", "en": "Data Structure"},
        "kisa": {"tr": "Verinin bilgisayar belleğinde düzenlenme ve saklanma biçimi.",
                 "en": "The way data is organized and stored in a computer's memory."},
        "aciklama": {
            "tr": "Doğru veri yapısını seçmek, bir algoritmanın hızını doğrudan etkiler: bir dizide "
                  "sıralı erişim hızlıyken, bir bağlı listede ortaya eleman eklemek daha kolaydır. Dizi, "
                  "bağlı liste, yığın, kuyruk, ağaç, graf ve hash tablosu en temel veri yapılarıdır.",
            "en": "Choosing the right data structure directly affects an algorithm's speed: an array "
                  "gives fast sequential access, while a linked list makes inserting in the middle "
                  "easier. Arrays, linked lists, stacks, queues, trees, graphs and hash tables are the "
                  "most fundamental data structures.",
        },
        "ilgili": ["dizi", "bagli_liste", "agac"],
    },
    {
        "id": "dizi",
        "baslik": {"tr": "Dizi (Array)", "en": "Array"},
        "kisa": {"tr": "Aynı türden elemanları bellekte art arda, sabit boyutlu bir blokta tutan yapı.",
                 "en": "A structure that holds same-type elements in a fixed-size, contiguous block of memory."},
        "aciklama": {
            "tr": "Dizideki her elemana, bellekteki konumu doğrudan hesaplanabildiği için anında (O(1)) "
                  "erişilebilir -- bu onu en hızlı okunabilir veri yapılarından biri yapar. Ama ortasına "
                  "yeni bir eleman eklemek, sonrasındaki her şeyi kaydırmayı gerektirdiğinden pahalıdır.",
            "en": "Any element in an array can be accessed instantly (O(1)) because its position in "
                  "memory can be computed directly -- making it one of the fastest data structures to "
                  "read from. But inserting a new element in the middle is expensive, since everything "
                  "after it has to shift.",
        },
        "ilgili": ["bagli_liste", "karmasiklik"],
    },
    {
        "id": "bagli_liste",
        "baslik": {"tr": "Bağlı Liste (Linked List)", "en": "Linked List"},
        "kisa": {"tr": "Her elemanın bir sonrakinin adresini tuttuğu, bellekte dağınık biçimde saklanabilen yapı.",
                 "en": "A structure where each element holds the address of the next, letting elements scatter in memory."},
        "aciklama": {
            "tr": "Bağlı listede eleman eklemek ya da çıkarmak yalnızca komşu bağlantıları güncellemeyi "
                  "gerektirdiğinden dizideki gibi kaydırma yapmaya gerek yoktur. Bunun bedeli, belirli "
                  "bir elemana ulaşmak için baştan itibaren bağlantıları tek tek takip etmek "
                  "zorunda olmasıdır -- doğrudan erişim yoktur.",
            "en": "Inserting or removing an element in a linked list only requires updating neighboring "
                  "links, so there's no shifting like in an array. The trade-off is that reaching a "
                  "specific element means following links one by one from the start -- there's no "
                  "direct access.",
        },
        "ilgili": ["dizi", "yigin", "kuyruk"],
    },
    {
        "id": "yigin",
        "baslik": {"tr": "Yığın (Stack)", "en": "Stack"},
        "kisa": {"tr": "Son eklenen elemanın ilk çıkarıldığı (LIFO) veri yapısı.",
                 "en": "A data structure where the last element added is the first one removed (LIFO)."},
        "aciklama": {
            "tr": "Bir tabak yığınına benzer: en üste konan tabak ilk alınandır. \"Geri al\" (undo) "
                  "özelliği, tarayıcı geçmişinde geri gitme ve fonksiyon çağrılarının takibi (call stack) "
                  "yığın mantığıyla çalışır.",
            "en": "It behaves like a stack of plates: the one placed on top is the first one taken off. "
                  "An \"undo\" feature, going back in browser history, and tracking function calls (the "
                  "call stack) all work on this last-in-first-out logic.",
        },
        "ilgili": ["kuyruk", "ozyineleme"],
    },
    {
        "id": "kuyruk",
        "baslik": {"tr": "Kuyruk (Queue)", "en": "Queue"},
        "kisa": {"tr": "İlk eklenen elemanın ilk çıkarıldığı (FIFO) veri yapısı.",
                 "en": "A data structure where the first element added is the first one removed (FIFO)."},
        "aciklama": {
            "tr": "Bir markette kasa sırası gibi çalışır: önce gelen önce hizmet alır. Yazdırma "
                  "sıraları, mesaj kuyrukları ve genişlik öncelikli arama (BFS) gibi birçok sistem bu "
                  "mantığa dayanır.",
            "en": "It works like a checkout line at a store: whoever arrives first gets served first. "
                  "Print queues, message queues and algorithms like breadth-first search (BFS) all rely "
                  "on this logic.",
        },
        "ilgili": ["yigin", "bfs"],
    },
    {
        "id": "agac",
        "baslik": {"tr": "Ağaç (Tree)", "en": "Tree"},
        "kisa": {"tr": "Bir kökten dallanan, hiyerarşik ilişkileri temsil eden veri yapısı.",
                 "en": "A hierarchical data structure that branches out from a single root."},
        "aciklama": {
            "tr": "Bir ağaçta her \"düğüm\"ün bir üst düğümü (ebeveyn) ve sıfır ya da daha fazla alt "
                  "düğümü (çocuk) vardır; döngü içermez. Dosya sistemleri, HTML'in DOM yapısı ve "
                  "veritabanı dizinleri (index) ağaç yapısıyla modellenir.",
            "en": "In a tree, every \"node\" has one parent and zero or more children, with no cycles. "
                  "File systems, a web page's DOM structure, and database indexes are all modeled as "
                  "trees.",
        },
        "ilgili": ["ikili_agac", "graf", "dosya_sistemi"],
    },
    {
        "id": "ikili_agac",
        "baslik": {"tr": "İkili Ağaç (Binary Tree)", "en": "Binary Tree"},
        "kisa": {"tr": "Her düğümün en fazla iki alt düğümü olabilen özel ağaç türü.",
                 "en": "A special tree where each node has at most two children."},
        "aciklama": {
            "tr": "Bir ikili arama ağacında, her düğümün sol alt ağacı kendisinden küçük, sağ alt ağacı "
                  "kendisinden büyük değerler içerir; bu düzen arama, ekleme ve silme işlemlerini "
                  "ortalama O(log n) sürede yapmayı mümkün kılar -- dengesiz bir ağaçta bu avantaj "
                  "kaybolabilir.",
            "en": "In a binary search tree, every node's left subtree holds smaller values and its right "
                  "subtree holds larger ones; this ordering lets search, insert and delete run in "
                  "average O(log n) time -- an advantage that can disappear if the tree becomes "
                  "unbalanced.",
        },
        "ilgili": ["agac", "ikili_arama", "karmasiklik"],
    },
    {
        "id": "hash_tablosu",
        "baslik": {"tr": "Hash Tablosu (Hash Table)", "en": "Hash Table"},
        "kisa": {"tr": "Anahtar-değer çiftlerini, bir özet fonksiyonu sayesinde ortalama sabit sürede erişilebilir saklayan yapı.",
                 "en": "A structure that stores key-value pairs with average constant-time access, thanks to a hash function."},
        "aciklama": {
            "tr": "Hash tablosu, her anahtarı bir hash fonksiyonuyla bir dizi konumuna eşleyerek neredeyse "
                  "anında arama yapılmasını sağlar -- Python'daki sözlük (dict) ve birçok dilde \"map\" "
                  "yapısı böyle çalışır. Farklı anahtarların aynı konuma düşmesine \"çarpışma\" (collision) "
                  "denir ve bu durum ek bir yöntemle çözülür.",
            "en": "A hash table maps every key to a position in an array via a hash function, enabling "
                  "near-instant lookups -- this is how Python's dict and the \"map\" structure in many "
                  "languages work. When two different keys land on the same position it's called a "
                  "\"collision\", which is resolved with an additional technique.",
        },
        "ilgili": ["hash_fonksiyonu", "veri_yapisi"],
    },
    {
        "id": "graf",
        "baslik": {"tr": "Graf (Graph)", "en": "Graph"},
        "kisa": {"tr": "Düğümleri ve aralarındaki bağlantıları (kenarları) temsil eden, ağaçtan daha genel bir yapı.",
                 "en": "A more general structure than a tree, representing nodes and the connections (edges) between them."},
        "aciklama": {
            "tr": "Bir grafta, ağaçtan farklı olarak bir düğümün birden fazla üst düğümü olabilir ve "
                  "döngüler oluşabilir. Sosyal ağlardaki arkadaşlık ilişkileri, yol haritaları ve "
                  "bilgisayar ağlarının topolojisi -- hatta internetin kendisi -- bir graf olarak "
                  "modellenebilir.",
            "en": "Unlike a tree, a node in a graph can have more than one parent and cycles can form. "
                  "Friendship connections on social networks, road maps, and the topology of computer "
                  "networks -- even the internet itself -- can be modeled as a graph.",
        },
        "ilgili": ["agac", "dfs", "bfs", "en_kisa_yol"],
    },
    {
        "id": "siralama_algoritmasi",
        "baslik": {"tr": "Sıralama Algoritması", "en": "Sorting Algorithm"},
        "kisa": {"tr": "Bir veri kümesini belirli bir sıraya (artan, azalan) dizmeye yarayan algoritma türü.",
                 "en": "An algorithm that arranges a data set into a defined order, ascending or descending."},
        "aciklama": {
            "tr": "Sıralama, bilgisayar biliminde en çok çalışılan problemlerden biridir çünkü arama ve "
                  "veri işleme gibi birçok başka işlemi hızlandırır -- örneğin sıralı bir dizide ikili "
                  "arama kullanılabilir. Hızlı sıralama ve birleştirme sıralaması gibi algoritmalar "
                  "ortalama O(n log n) sürede çalışırken, balon sıralama gibi basit yöntemler O(n²) "
                  "sürede çalışır.",
            "en": "Sorting is one of the most studied problems in computer science because it speeds up "
                  "many other operations, like being able to run binary search on a sorted array. "
                  "Algorithms like quicksort and merge sort run in average O(n log n) time, while "
                  "simpler methods like bubble sort run in O(n²).",
        },
        "ilgili": ["hizli_siralama", "birlestirme_siralamasi", "karmasiklik"],
    },
    {
        "id": "hizli_siralama",
        "baslik": {"tr": "Hızlı Sıralama (Quicksort)", "en": "Quicksort"},
        "kisa": {"tr": "Bir \"eksen\" eleman seçip listeyi bölerek çalışan, pratikte en hızlı sıralama algoritmalarından biri.",
                 "en": "A sorting algorithm that picks a \"pivot\" element and partitions the list, one of the fastest in practice."},
        "aciklama": {
            "tr": "Quicksort, bir eksen eleman seçer, listeyi ondan küçük ve büyük elemanlar olarak ikiye "
                  "böler, sonra her iki yarıyı da özyinelemeli (recursive) olarak sıralar. Ortalama "
                  "durumda O(n log n) hızındadır, ama kötü seçilmiş bir eksenle en kötü durumda O(n²)'ye "
                  "düşebilir -- \"böl ve fethet\" stratejisinin klasik bir örneğidir.",
            "en": "Quicksort picks a pivot element, splits the list into elements smaller and larger than "
                  "it, then recursively sorts each half. It runs at O(n log n) on average, but can "
                  "degrade to O(n²) in the worst case with a poorly chosen pivot -- a textbook example of "
                  "the \"divide and conquer\" strategy.",
        },
        "ilgili": ["siralama_algoritmasi", "bol_ve_fethet", "ozyineleme"],
    },
    {
        "id": "birlestirme_siralamasi",
        "baslik": {"tr": "Birleştirme Sıralaması (Merge Sort)", "en": "Merge Sort"},
        "kisa": {"tr": "Listeyi ikiye bölüp her yarıyı ayrı ayrı sıraladıktan sonra birleştiren, kararlı sıralama algoritması.",
                 "en": "A stable sorting algorithm that splits the list in half, sorts each half, then merges them."},
        "aciklama": {
            "tr": "Birleştirme sıralaması her durumda garantili O(n log n) hızında çalışır -- quicksort'un "
                  "aksine en kötü durumda bile yavaşlamaz -- ama bunun bedeli olarak ekstra bellek "
                  "kullanır. \"Kararlı\" olması, eşit değerli elemanların göreceli sırasını koruması "
                  "anlamına gelir.",
            "en": "Merge sort guarantees O(n log n) performance in every case -- unlike quicksort it "
                  "never degrades in the worst case -- at the cost of using extra memory. Being "
                  "\"stable\" means it preserves the relative order of elements with equal values.",
        },
        "ilgili": ["hizli_siralama", "bol_ve_fethet"],
    },
    {
        "id": "dogrusal_arama",
        "baslik": {"tr": "Doğrusal Arama (Linear Search)", "en": "Linear Search"},
        "kisa": {"tr": "Bir listeyi baştan sona tek tek tarayarak aranan elemanı bulma yöntemi.",
                 "en": "Finding an element by checking a list one item at a time, from start to finish."},
        "aciklama": {
            "tr": "Doğrusal arama en basit arama yöntemidir ve listenin sıralı olmasını gerektirmez, ama "
                  "en kötü durumda tüm listeyi gezmek gerekebileceğinden O(n) sürer. Küçük listelerde ya "
                  "da sıralı olmayan verilerde makul bir seçenektir.",
            "en": "Linear search is the simplest search method and doesn't require the list to be "
                  "sorted, but runs in O(n) time since the worst case may require scanning the whole "
                  "list. It's a reasonable choice for small lists or unsorted data.",
        },
        "ilgili": ["ikili_arama", "karmasiklik"],
    },
    {
        "id": "ikili_arama",
        "baslik": {"tr": "İkili Arama (Binary Search)", "en": "Binary Search"},
        "kisa": {"tr": "Sıralı bir listede, her adımda arama alanını yarıya indirerek çok hızlı arama yapan yöntem.",
                 "en": "A search method on a sorted list that halves the search space at every step."},
        "aciklama": {
            "tr": "İkili arama, bir sözlükte bir kelimeyi bulmaya benzer: ortadaki sayfaya bakıp aranan "
                  "kelimenin ondan önce mi sonra mı geldiğine karar verir ve aramayı o yarıyla sınırlar. "
                  "Bu sayede bir milyon elemanlı sıralı bir listede bile yalnızca ~20 karşılaştırmayla "
                  "sonuca ulaşır (O(log n)) -- ama liste sıralı olmak zorundadır.",
            "en": "Binary search is like finding a word in a dictionary: check the middle page, decide "
                  "whether the target comes before or after it, then limit the search to that half. This "
                  "means even a sorted list of a million elements can be searched in roughly 20 "
                  "comparisons (O(log n)) -- but the list has to be sorted first.",
        },
        "ilgili": ["dogrusal_arama", "siralama_algoritmasi", "ikili_agac"],
    },
    {
        "id": "ozyineleme",
        "baslik": {"tr": "Özyineleme (Recursion)", "en": "Recursion"},
        "kisa": {"tr": "Bir fonksiyonun, bir problemi çözerken kendi kendini çağırması.",
                 "en": "A function solving a problem by calling itself."},
        "aciklama": {
            "tr": "Özyinelemeli bir fonksiyon, büyük bir problemi daha küçük, kendisiyle aynı yapıdaki alt "
                  "problemlere böler ve en basit \"taban durumu\"na ulaşana kadar kendini tekrar çağırır. "
                  "Ağaç yapılarını gezmek ve böl-ve-fethet algoritmaları yazmak için doğal bir "
                  "yaklaşımdır, ama taban durumu unutulursa sonsuz döngüye (stack overflow) yol açar.",
            "en": "A recursive function breaks a large problem into smaller subproblems of the same "
                  "shape, calling itself again until it reaches the simplest \"base case\". It's a "
                  "natural fit for traversing tree structures and writing divide-and-conquer algorithms, "
                  "but forgetting the base case leads to infinite recursion (a stack overflow).",
        },
        "ilgili": ["yigin", "hizli_siralama", "bol_ve_fethet"],
    },
    {
        "id": "bol_ve_fethet",
        "baslik": {"tr": "Böl ve Fethet (Divide and Conquer)", "en": "Divide and Conquer"},
        "kisa": {"tr": "Bir problemi küçük alt problemlere bölüp her birini ayrı çözen, sonra sonuçları birleştiren strateji.",
                 "en": "A strategy that splits a problem into smaller subproblems, solves each, then combines the results."},
        "aciklama": {
            "tr": "Böl ve fethet, üç adımdan oluşur: böl (problemi alt problemlere ayır), fethet (her alt "
                  "problemi -- genellikle özyinelemeli olarak -- çöz), birleştir (alt sonuçları asıl "
                  "çözüme dönüştür). Hızlı sıralama ve birleştirme sıralaması bu stratejinin klasik "
                  "örnekleridir.",
            "en": "Divide and conquer has three steps: divide (break the problem into subproblems), "
                  "conquer (solve each subproblem, usually recursively), and combine (merge the "
                  "sub-results into the final answer). Quicksort and merge sort are textbook examples of "
                  "this strategy.",
        },
        "ilgili": ["hizli_siralama", "birlestirme_siralamasi", "ozyineleme"],
    },
    {
        "id": "acgozlu_algoritma",
        "baslik": {"tr": "Açgözlü Algoritma (Greedy Algorithm)", "en": "Greedy Algorithm"},
        "kisa": {"tr": "Her adımda o an için en iyi görünen seçimi yapan, geri dönmeyen algoritma yaklaşımı.",
                 "en": "An approach that makes the locally best choice at every step, without backtracking."},
        "aciklama": {
            "tr": "Açgözlü bir algoritma gelecekteki sonuçları hesaba katmaz; yalnızca o anki en iyi "
                  "seçimi yapar ve asla geri dönmez. Bazı problemlerde (en az sayıda madeni parayla para "
                  "üstü verme gibi) bu yaklaşım en iyi sonucu garanti eder, ama her problemde işe "
                  "yaramaz -- bazen küresel en iyi çözümü kaçırır.",
            "en": "A greedy algorithm doesn't account for future consequences; it just makes the best "
                  "choice available right now and never backtracks. For some problems -- making change "
                  "with the fewest coins, for instance -- this approach guarantees the optimal result, "
                  "but it doesn't work for every problem; it can miss the globally best solution.",
        },
        "ilgili": ["dinamik_programlama", "en_kisa_yol"],
    },
    {
        "id": "dinamik_programlama",
        "baslik": {"tr": "Dinamik Programlama", "en": "Dynamic Programming"},
        "kisa": {"tr": "Alt problemlerin sonuçlarını saklayarak aynı hesaplamayı tekrar tekrar yapmaktan kaçınan teknik.",
                 "en": "A technique that stores subproblem results to avoid repeating the same computation over and over."},
        "aciklama": {
            "tr": "Dinamik programlama, bir problemi örtüşen alt problemlere ayrılabildiğinde işe yarar: "
                  "her alt problemin sonucu bir kez hesaplanıp saklanır (\"ezberleme\"/memoization), "
                  "tekrar ihtiyaç duyulduğunda yeniden hesaplamak yerine doğrudan okunur. Fibonacci "
                  "dizisini hesaplamak, saf özyinelemeyle katlanarak yavaşlarken dinamik programlamayla "
                  "doğrusal sürede çözülebilir.",
            "en": "Dynamic programming pays off when a problem can be broken into overlapping "
                  "subproblems: each subproblem's result is computed once and cached (\"memoization\"), "
                  "then read directly instead of recomputed the next time it's needed. Computing the "
                  "Fibonacci sequence, exponentially slow with plain recursion, becomes linear-time with "
                  "dynamic programming.",
        },
        "ilgili": ["acgozlu_algoritma", "ozyineleme", "onbellek"],
    },
    {
        "id": "dfs",
        "baslik": {"tr": "Derinlik Öncelikli Arama (DFS)", "en": "Depth-First Search (DFS)"},
        "kisa": {"tr": "Bir dalı sonuna kadar takip ettikten sonra geri dönüp diğerini deneyen graf/ağaç gezinme yöntemi.",
                 "en": "A graph/tree traversal that follows one branch all the way down before backtracking to try another."},
        "aciklama": {
            "tr": "DFS, genellikle bir yığın (ya da özyineleme) kullanarak bir düğümden başlar, "
                  "gidebildiği kadar derine iner, çıkmaza girdiğinde geri döner ve ziyaret edilmemiş bir "
                  "dalı dener. Labirent çözmek ya da bir dosya ağacını tam olarak gezmek için doğal bir "
                  "yaklaşımdır.",
            "en": "DFS, typically using a stack (or recursion), starts at a node, goes as deep as it "
                  "can, backtracks when it hits a dead end, and tries an unvisited branch. It's a "
                  "natural fit for solving a maze or fully traversing a file tree.",
        },
        "ilgili": ["bfs", "graf", "yigin"],
    },
    {
        "id": "bfs",
        "baslik": {"tr": "Genişlik Öncelikli Arama (BFS)", "en": "Breadth-First Search (BFS)"},
        "kisa": {"tr": "Bir düğümden başlayıp önce tüm komşularını, sonra komşularının komşularını gezen yöntem.",
                 "en": "A traversal that starts at a node and visits all its neighbors before moving further out."},
        "aciklama": {
            "tr": "BFS, bir kuyruk kullanarak düğümleri \"katman katman\" gezer; bu özelliği sayesinde "
                  "ağırlıksız bir grafta iki düğüm arasındaki en kısa yolu bulmak için doğal bir "
                  "yöntemdir. Sosyal ağlarda \"iki kişi arasındaki en kısa bağlantı\"yı bulmak gibi "
                  "problemlerde kullanılır.",
            "en": "BFS uses a queue to visit nodes \"layer by layer\", which makes it a natural way to "
                  "find the shortest path between two nodes in an unweighted graph. It's used for "
                  "problems like finding the shortest connection between two people on a social network.",
        },
        "ilgili": ["dfs", "kuyruk", "en_kisa_yol"],
    },
    {
        "id": "en_kisa_yol",
        "baslik": {"tr": "En Kısa Yol Algoritması (Dijkstra)", "en": "Shortest Path Algorithm (Dijkstra)"},
        "kisa": {"tr": "Ağırlıklı bir grafta iki düğüm arasındaki en düşük maliyetli yolu bulan algoritma.",
                 "en": "An algorithm that finds the lowest-cost path between two nodes in a weighted graph."},
        "aciklama": {
            "tr": "Dijkstra algoritması, her kenarın bir \"ağırlığı\" (mesafe, süre, maliyet) olduğu bir "
                  "grafta başlangıç düğümünden her diğer düğüme olan en kısa yolu açgözlü biçimde, her "
                  "adımda en yakın bilinmeyen düğümü seçerek bulur. Harita uygulamalarındaki rota "
                  "bulma özelliğinin temelinde bu tür algoritmalar yatar.",
            "en": "Dijkstra's algorithm greedily finds the shortest path from a start node to every "
                  "other node in a graph where each edge has a \"weight\" (distance, time, cost), always "
                  "picking the nearest unvisited node at each step. Algorithms like this underlie the "
                  "route-finding feature in map applications.",
        },
        "ilgili": ["graf", "acgozlu_algoritma", "bfs"],
    },
    {
        "id": "onbellek",
        "baslik": {"tr": "Önbellek (Cache)", "en": "Cache"},
        "kisa": {"tr": "Sık erişilen verinin daha hızlı bir yerde geçici olarak tutulmasıyla tekrar hesaplamayı önleyen teknik.",
                 "en": "Temporarily storing frequently used data somewhere faster, to avoid recomputing or refetching it."},
        "aciklama": {
            "tr": "Önbellek, bir web sayfasının görsellerini tarayıcıda saklamaktan, bir CPU'nun sık "
                  "kullanılan veriyi kendi hızlı belleğinde tutmasına kadar her seviyede karşımıza çıkar. "
                  "Temel fikir basittir: aynı veriye ya da sonuca tekrar ihtiyaç duyulacaksa, onu baştan "
                  "hesaplamak ya da yeniden indirmek yerine saklayıp doğrudan kullanmak.",
            "en": "Caching shows up at every level, from a browser storing a web page's images to a CPU "
                  "keeping frequently used data in its own fast memory. The core idea is simple: if the "
                  "same data or result will be needed again, store it and reuse it directly instead of "
                  "recomputing or re-fetching it from scratch.",
        },
        "ilgili": ["dinamik_programlama", "hash_tablosu"],
    },
    {
        "id": "p_np_problemi",
        "baslik": {"tr": "P ve NP Problemi", "en": "The P vs NP Problem"},
        "kisa": {"tr": "Çözümü hızlıca doğrulanabilen her problemin hızlıca da çözülüp çözülemeyeceğini soran, bilgisayar biliminin en büyük açık sorusu.",
                 "en": "Computer science's biggest open question: can every problem whose solution is quickly verifiable also be quickly solved?"},
        "aciklama": {
            "tr": "P, hızlı (polinom zamanda) çözülebilen problemlerin kümesidir; NP ise çözümü verildiğinde "
                  "o çözümün doğruluğu hızlıca kontrol edilebilen problemlerin kümesidir. P=NP mi "
                  "sorusu, hızlı doğrulanabilen her şeyin hızlı da çözülüp çözülemeyeceğini sorar -- "
                  "çoğu bilgisayar bilimci hayır olduğuna inanır, ama bu kanıtlanmış değildir. Modern "
                  "şifrelemenin güvenliği büyük ölçüde bu sorunun yanıtının \"hayır\" olmasına dayanır.",
            "en": "P is the set of problems solvable quickly (in polynomial time); NP is the set of "
                  "problems whose proposed solution can be checked quickly once you have one. The P=NP "
                  "question asks whether everything quickly verifiable can also be quickly solved -- most "
                  "computer scientists believe the answer is no, but it has never been proven. Much of "
                  "modern encryption's security rests on that answer staying no.",
        },
        "ilgili": ["karmasiklik", "rsa"],
    },
]
