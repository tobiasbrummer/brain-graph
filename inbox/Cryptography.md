# [Cryptography](https://en.wikipedia.org/wiki/Cryptography)
+id:01KCA7DRD0SG5Q0D8JTJX4FA4J

## Summary

Cryptography, or cryptology (from [Ancient Greek](https://en.wikipedia.org/wiki/Ancient_Greek): κρυπτός, romanized: kryptós "hidden, secret"; and γράφειν graphein, "to write", or -λογία -logia, "study", respectively), is the practice and study of techniques for secure communication in the presence of adversarial behavior. More generally, cryptography is about constructing and analyzing protocols that prevent third parties or the public from reading private messages. Modern cryptography exists at the intersection of the disciplines of mathematics, computer science, information security, electrical engineering, digital signal processing, physics, and others. Core concepts related to information security (data confidentiality, data integrity, authentication and non-repudiation) are also central to cryptography. Practical applications of cryptography include electronic commerce, chip-based payment cards, digital currencies, computer passwords and military communications.

Cryptography prior to the modern age was effectively synonymous with encryption, converting readable information (plaintext) to unintelligible nonsense text (ciphertext), which can only be read by reversing the process (decryption). The sender of an encrypted (coded) message shares the decryption (decoding) technique only with the intended recipients to preclude access from adversaries. The cryptography literature often uses the names "Alice" (or "A") for the sender, "Bob" (or "B") for the intended recipient, and "Eve" (or "E") for the eavesdropping adversary. Since the development of rotor cipher machines in World War I and the advent of computers in World War II, cryptography methods have become increasingly complex and their applications more varied.

Modern cryptography is heavily based on mathematical theory and computer science practice; cryptographic algorithms are designed around computational hardness assumptions, making such algorithms hard to break in actual practice by any adversary. While it is theoretically possible to break into a well-designed system, it is infeasible in actual practice to do so. Such schemes, if well designed, are therefore termed "computationally secure". Theoretical advances (e.g., improvements in integer factorization algorithms) and faster computing technology require these designs to be continually reevaluated and, if necessary, adapted. Information-theoretically secure schemes that provably cannot be broken even with unlimited computing power, such as the one-time pad, are much more difficult to use in practice than the best theoretically breakable but computationally secure schemes.

The growth of cryptographic technology has raised a number of legal issues in the Information Age. Cryptography's potential for use as a tool for espionage and sedition has led many governments to classify it as a weapon and to limit or even prohibit its use and export. In some jurisdictions where the use of cryptography is legal, laws permit investigators to compel the disclosure of encryption keys for documents relevant to an investigation. Cryptography also plays a major role in digital rights management and copyright infringement disputes with regard to digital media.

## Terminology

The first use of the term "cryptograph" (as opposed to "cryptogram") dates back to the 19th century – originating from "The Gold-Bug", a story by Edgar Allan Poe.

Until modern times, cryptography referred almost exclusively to "encryption", which is the process of converting ordinary information (called plaintext) into an unintelligible form (called ciphertext). Decryption is the reverse, in other words, moving from the unintelligible ciphertext back to plaintext. A cipher (or cypher) is a pair of algorithms that carry out the encryption and the reversing decryption. The detailed operation of a cipher is controlled both by the algorithm and, in each instance, by a "key". The key is a secret (ideally known only to the communicants), usually a string of characters (ideally short so it can be remembered by the user), which is needed to decrypt the ciphertext. In formal mathematical terms, a "cryptosystem" is the ordered list of elements of finite possible plaintexts, finite possible cyphertexts, finite possible keys, and the encryption and decryption algorithms that correspond to each key. Keys are important both formally and in actual practice, as ciphers without variable keys can be trivially broken with only the knowledge of the cipher used and are therefore useless (or even counter-productive) for most purposes. Historically, ciphers were often used directly for encryption or decryption without additional procedures such as authentication or integrity checks.

There are two main types of cryptosystems: symmetric and asymmetric. In symmetric systems, the only ones known until the 1970s, the same secret key encrypts and decrypts a message. Data manipulation in symmetric systems is significantly faster than in asymmetric systems. Asymmetric systems use a "public key" to encrypt a message and a related "private key" to decrypt it. The advantage of asymmetric systems is that the public key can be freely published, allowing parties to establish secure communication without having a shared secret key. In practice, asymmetric systems are used to first exchange a secret key, and then secure communication proceeds via a more efficient symmetric system using that key. Examples of asymmetric systems include [Diffie–Hellman key exchange](https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange), RSA (Rivest–Shamir–Adleman), ECC ([Elliptic Curve Cryptography](https://en.wikipedia.org/wiki/Elliptic-curve_cryptography)), and Post-quantum cryptography. Secure symmetric algorithms include the commonly used AES ([Advanced Encryption Standard](https://en.wikipedia.org/wiki/Advanced_Encryption_Standard)) which replaced the older DES ([Data Encryption Standard](https://en.wikipedia.org/wiki/Data_Encryption_Standard)). Insecure symmetric algorithms include children's language tangling schemes such as Pig Latin or other cant, and all historical cryptographic schemes, however seriously intended, prior to the invention of the one-time pad early in the 20th century.

In colloquial use, the term "code" is often used to mean any method of encryption or concealment of meaning. However, in cryptography, code has a more specific meaning: the replacement of a unit of plaintext (i.e., a meaningful word or phrase) with a code word (for example, "wallaby" replaces "attack at dawn"). A cypher, in contrast, is a scheme for changing or substituting an element below such a level (a letter, a syllable, or a pair of letters, etc.) to produce a cyphertext.

[Cryptanalysis](https://en.wikipedia.org/wiki/Cryptanalysis) is the term used for the study of methods for obtaining the meaning of encrypted information without access to the key normally required to do so; i.e., it is the study of how to "crack" encryption algorithms or their implementations.

Some use the terms "cryptography" and "cryptology" interchangeably in English, while others (including US military practice generally) use "cryptography" to refer specifically to the use and practice of cryptographic techniques and "cryptology" to refer to the combined study of cryptography and cryptanalysis. English is more flexible than several other languages in which "cryptology" (done by cryptologists) is always used in the second sense above. RFC 2828 advises that steganography is sometimes included in cryptology.

The study of characteristics of languages that have some application in cryptography or cryptology (e.g. frequency data, letter combinations, universal patterns, etc.) is called cryptolinguistics. Cryptolingusitics is especially used in military intelligence applications for deciphering foreign communications.

## History

Before the modern era, cryptography focused on message confidentiality (i.e., encryption)—conversion of messages from a comprehensible form into an incomprehensible one and back again at the other end, rendering it unreadable by interceptors or eavesdroppers without secret knowledge (namely the key needed for decryption of that message). Encryption attempted to ensure secrecy in communication, such as those of spies, military leaders, and diplomats. In recent decades, the field has expanded beyond confidentiality concerns to include techniques for message integrity checking, sender/receiver identity authentication, digital signatures, interactive proofs and secure computation, among others.

### Classic cryptography

The main classical cipher types are transposition ciphers, which rearrange the order of letters in a message (e.g., 'hello world' becomes 'ehlol owrdl' in a trivially simple rearrangement scheme), and substitution ciphers, which systematically replace letters or groups of letters with other letters or groups of letters (e.g., 'fly at once' becomes 'gmz bu podf' by replacing each letter with the one following it in the Latin alphabet). Simple versions of either have never offered much confidentiality from enterprising opponents. An early substitution cipher was the [Caesar cipher](https://en.wikipedia.org/wiki/Caesar_cipher), in which each letter in the plaintext was replaced by a letter three positions further down the alphabet. Suetonius reports that Julius Caesar used it with a shift of three to communicate with his generals. [Atbash](https://en.wikipedia.org/wiki/Atbash) is an example of an early Hebrew cipher. The earliest known use of cryptography is some carved ciphertext on stone in Egypt (c. 1900 BCE), but this may have been done for the amusement of literate observers rather than as a way of concealing information.

The Greeks of Classical times are said to have known of ciphers (e.g., the scytale transposition cipher claimed to have been used by the [Sparta](https://en.wikipedia.org/wiki/Sparta)n military). Steganography (i.e., hiding even the existence of a message so as to keep it confidential) was also first developed in ancient times. An early example, from [Herodotus](https://en.wikipedia.org/wiki/Herodotus), was a message tattooed on a slave's shaved head and concealed under the regrown hair. Other steganography methods involve 'hiding in plain sight,' such as using a music cipher to disguise an encrypted message within a regular piece of sheet music. More modern examples of steganography include the use of invisible ink, microdots, and digital watermarks to conceal information.

In India, the 2000-year-old Kama Sutra of [Vātsyāyana](https://en.wikipedia.org/wiki/V%C4%81tsy%C4%81yana) speaks of two different kinds of ciphers called Kautiliyam and Mulavediya. In the Kautiliyam, the cipher letter substitutions are based on phonetic relations, such as vowels becoming consonants. In the Mulavediya, the cipher alphabet consists of pairing letters and using the reciprocal ones.

In Sassanid Persia, there were two secret scripts, according to the Muslim author Ibn al-Nadim: the šāh-dabīrīya (literally "King's script") which was used for official correspondence, and the rāz-saharīya which was used to communicate secret messages with other countries.

David Kahn notes in The Codebreakers that modern cryptology originated among the [Arabs](https://en.wikipedia.org/wiki/Arabs), the first people to systematically document cryptanalytic methods. Al-Khalil (717–786) wrote the Book of Cryptographic Messages, which contains the first use of permutations and combinations to list all possible Arabic words with and without vowels.


[[Cipher](https://en.wikipedia.org/wiki/Cipher)text](https://en.wikipedia.org/wiki/[Cipher](https://en.wikipedia.org/wiki/Cipher)text)s produced by a classical cipher (and some modern ciphers) will reveal statistical information about the plaintext, and that information can often be used to break the cipher. After the discovery of frequency analysis, nearly all such ciphers could be broken by an informed attacker. Such classical ciphers still enjoy popularity today, though mostly as puzzles (see cryptogram). The Arab mathematician and polymath [Al-Kindi](https://en.wikipedia.org/wiki/Al-Kindi) wrote a book on cryptography entitled Risalah fi Istikhraj al-Mu'amma (Manuscript for the Deciphering Cryptographic Messages), which described the first known use of frequency analysis cryptanalysis techniques.


[Language](https://en.wikipedia.org/wiki/Language) letter frequencies may offer little help for some extended historical encryption techniques such as homophonic cipher that tend to flatten the frequency distribution. For those ciphers, language letter group (or n-gram) frequencies may provide an attack.

Essentially all ciphers remained vulnerable to cryptanalysis using the frequency analysis technique until the development of the polyalphabetic cipher, most clearly by [Leon Battista Alberti](https://en.wikipedia.org/wiki/Leon_Battista_Alberti) around the year 1467, though there is some indication that it was already known to [Al-Kindi](https://en.wikipedia.org/wiki/Al-Kindi). Alberti's innovation was to use different ciphers (i.e., substitution alphabets) for various parts of a message (perhaps for each successive plaintext letter at the limit). He also invented what was probably the first automatic cipher device, a wheel that implemented a partial realization of his invention. In the [Vigenère cipher](https://en.wikipedia.org/wiki/Vigen%C3%A8re_cipher), a polyalphabetic cipher, encryption uses a key word, which controls letter substitution depending on which letter of the key word is used. In the mid-19th century [Charles Babbage](https://en.wikipedia.org/wiki/Charles_Babbage) showed that the [Vigenère cipher](https://en.wikipedia.org/wiki/Vigen%C3%A8re_cipher) was vulnerable to [Kasiski examination](https://en.wikipedia.org/wiki/Kasiski_examination), but this was first published about ten years later by Friedrich Kasiski.

Although frequency analysis can be a powerful and general technique against many ciphers, encryption has still often been effective in practice, as many a would-be cryptanalyst was unaware of the technique. Breaking a message without using frequency analysis essentially required knowledge of the cipher used and perhaps of the key involved, thus making espionage, bribery, burglary, defection, etc., more attractive approaches to the cryptanalytically uninformed. It was finally explicitly recognized in the 19th century that secrecy of a cipher's algorithm is not a sensible nor practical safeguard of message security; in fact, it was further realized that any adequate cryptographic scheme (including ciphers) should remain secure even if the adversary fully understands the cipher algorithm itself. Security of the key used should alone be sufficient for a good cipher to maintain confidentiality under an attack. This fundamental principle was first explicitly stated in 1883 by [Auguste Kerckhoffs](https://en.wikipedia.org/wiki/Auguste_Kerckhoffs) and is generally called Kerckhoffs's Principle; alternatively and more bluntly, it was restated by [Claude Shannon](https://en.wikipedia.org/wiki/Claude_Shannon), the inventor of information theory and the fundamentals of theoretical cryptography, as Shannon's Maxim—'the enemy knows the system'.

Different physical devices and aids have been used to assist with ciphers. One of the earliest may have been the scytale of ancient Greece, a rod supposedly used by the [Sparta](https://en.wikipedia.org/wiki/Sparta)ns as an aid for a transposition cipher. In medieval times, other aids were invented such as the cipher grille, which was also used for a kind of steganography. With the invention of polyalphabetic ciphers came more sophisticated aids such as Alberti's own cipher disk, Johannes Trithemius' tabula recta scheme, and Thomas Jefferson's wheel cypher (not publicly known, and reinvented independently by [Bazeries](https://en.wikipedia.org/wiki/%C3%89tienne_Bazeries) around 1900). Many mechanical encryption/decryption devices were invented early in the 20th century, and several patented, among them rotor machines—famously including the Enigma machine used by the German government and military from the late 1920s and during World War II. The ciphers implemented by better quality examples of these machine designs brought about a substantial increase in cryptanalytic difficulty after WWI.

### Early computer-era cryptography

[Cryptanalysis](https://en.wikipedia.org/wiki/Cryptanalysis) of the new mechanical ciphering devices proved to be both difficult and laborious. In the United Kingdom, cryptanalytic efforts at [Bletchley Park](https://en.wikipedia.org/wiki/Bletchley_Park) during WWII spurred the development of more efficient means for carrying out repetitive tasks, such as military code breaking (decryption). This culminated in the development of the Colossus, the world's first fully electronic, digital, programmable computer, which assisted in the decryption of ciphers generated by the German Army's [Lorenz SZ40/42](https://en.wikipedia.org/wiki/Lorenz_cipher) machine.

Extensive open academic research into cryptography is relatively recent, beginning in the mid-1970s. In the early 1970s IBM personnel designed the [Data Encryption Standard](https://en.wikipedia.org/wiki/Data_Encryption_Standard) (DES) algorithm that became the first federal government cryptography standard in the United States. In 1976 Whitfield Diffie and Martin Hellman published the [Diffie–Hellman key exchange](https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange) algorithm. In 1977 the RSA algorithm was published in [Martin Gardner](https://en.wikipedia.org/wiki/Martin_Gardner)'s Scientific American column. Since then, cryptography has become a widely used tool in communications, computer networks, and computer security generally.

Some modern cryptographic techniques can only keep their keys secret if certain mathematical problems are intractable, such as the integer factorization or the discrete logarithm problems, so there are deep connections with abstract mathematics. There are very few cryptosystems that are proven to be unconditionally secure. The one-time pad is one, and was proven to be so by [Claude Shannon](https://en.wikipedia.org/wiki/Claude_Shannon). There are a few important algorithms that have been proven secure under certain assumptions. For example, the infeasibility of factoring extremely large integers is the basis for believing that RSA is secure, and some other systems, but even so, proof of unbreakability is unavailable since the underlying mathematical problem remains open. In practice, these are widely used, and are believed unbreakable in practice by most competent observers. There are systems similar to RSA, such as one by Michael O. Rabin that are provably secure provided factoring n = pq is impossible; it is quite unusable in practice. The discrete logarithm problem is the basis for believing some other cryptosystems are secure, and again, there are related, less practical systems that are provably secure relative to the solvability or insolvability discrete log problem.

As well as being aware of cryptographic history, cryptographic algorithm and system designers must also sensibly consider probable future developments while working on their designs. For instance, continuous improvements in computer processing power have increased the scope of brute-force attacks, so when specifying key lengths, the required key lengths are similarly advancing. The potential impact of quantum computing are already being considered by some cryptographic system designers developing post-quantum cryptography. The announced imminence of small implementations of these machines may be making the need for preemptive caution rather more than merely speculative.

## Modern cryptography

[Claude Shannon](https://en.wikipedia.org/wiki/Claude_Shannon)'s two papers, his 1948 paper on information theory, and especially his 1949 paper on cryptography, laid the foundations of modern cryptography and provided a mathematical basis for future cryptography. His 1949 paper has been noted as having provided a "solid theoretical basis for cryptography and for cryptanalysis", and as having turned cryptography from an "art to a science". As a result of his contributions and work, he has been described as the "founding father of modern cryptography".

Prior to the early 20th century, cryptography was mainly concerned with linguistic and lexicographic patterns. Since then cryptography has broadened in scope, and now makes extensive use of mathematical subdisciplines, including information theory, computational complexity, statistics, combinatorics, abstract algebra, number theory, and finite mathematics. Cryptography is also a branch of engineering, but an unusual one since it deals with active, intelligent, and malevolent opposition; other kinds of engineering (e.g., civil or chemical engineering) need deal only with neutral natural forces. There is also active research examining the relationship between cryptographic problems and quantum physics.

Just as the development of digital computers and electronics helped in cryptanalysis, it made possible much more complex ciphers. Furthermore, computers allowed for the encryption of any kind of data representable in any binary format, unlike classical ciphers which only encrypted written language texts; this was new and significant. Computer use has thus supplanted linguistic cryptography, both for cipher design and cryptanalysis. Many computer ciphers can be characterized by their operation on binary bit sequences (sometimes in groups or blocks), unlike classical and mechanical schemes, which generally manipulate traditional characters (i.e., letters and digits) directly. However, computers have also assisted cryptanalysis, which has compensated to some extent for increased cipher complexity. Nonetheless, good modern ciphers have stayed ahead of cryptanalysis; it is typically the case that use of a quality cipher is very efficient (i.e., fast and requiring few resources, such as memory or CPU capability), while breaking it requires an effort many orders of magnitude larger, and vastly larger than that required for any classical cipher, making cryptanalysis so inefficient and impractical as to be effectively impossible.

Research into post-quantum cryptography (PQC) has intensified because practical quantum computers would break widely deployed public-key systems such as RSA, Diffie–Hellman and ECC. A 2017 review in Nature surveys the leading PQC families—lattice-based, code-based, multivariate-quadratic and hash-based schemes—and stresses that standardisation and deployment should proceed well before large-scale quantum machines become available.

### Symmetric-key cryptography

Symmetric-key cryptography refers to encryption methods in which both the sender and receiver share the same key (or, less commonly, in which their keys are different, but related in an easily computable way). This was the only kind of encryption publicly known until June 1976.


Symmetric key ciphers are implemented as either block ciphers or stream ciphers. A block cipher enciphers input in blocks of plaintext as opposed to individual characters, the input form used by a stream cipher.

The [Data Encryption Standard](https://en.wikipedia.org/wiki/Data_Encryption_Standard) (DES) and the [Advanced Encryption Standard](https://en.wikipedia.org/wiki/Advanced_Encryption_Standard) (AES) are block cipher designs that have been designated cryptography standards by the US government (though DES's designation was finally withdrawn after the AES was adopted). Despite its deprecation as an official standard, DES (especially its still-approved and much more secure triple-DES variant) remains quite popular; it is used across a wide range of applications, from ATM encryption to e-mail privacy and secure remote access. Many other block ciphers have been designed and released, with considerable variation in quality. Many, even some designed by capable practitioners, have been thoroughly broken, such as FEAL.

[Stream cipher](https://en.wikipedia.org/wiki/Stream_cipher)s, in contrast to the 'block' type, create an arbitrarily long stream of key material, which is combined with the plaintext bit-by-bit or character-by-character, somewhat like the one-time pad. In a stream cipher, the output stream is created based on a hidden internal state that changes as the cipher operates. That internal state is initially set up using the secret key material. RC4 is a widely used stream cipher. [[Block cipher](https://en.wikipedia.org/wiki/Block_cipher)s](https://en.wikipedia.org/wiki/Block_cipher) can be used as stream ciphers by generating blocks of a keystream (in place of a Pseudorandom number generator) and applying an XOR operation to each bit of the plaintext with each bit of the keystream.

[Message authentication](https://en.wikipedia.org/wiki/Message_authentication) codes (MACs) are much like cryptographic hash functions, except that a secret key can be used to authenticate the hash value upon receipt; this additional complication blocks an attack scheme against bare digest algorithms, and so has been thought worth the effort. Cryptographic hash functions are a third type of cryptographic algorithm. They take a message of any length as input, and output a short, fixed-length hash, which can be used in (for example) a digital signature. For good hash functions, an attacker cannot find two messages that produce the same hash. [MD4](https://en.wikipedia.org/wiki/MD4) is a long-used hash function that is now broken; MD5, a strengthened variant of [MD4](https://en.wikipedia.org/wiki/MD4), is also widely used but broken in practice. The US National Security Agency developed the Secure Hash [Algorithm](https://en.wikipedia.org/wiki/Algorithm) series of MD5-like hash functions: SHA-0 was a flawed algorithm that the agency withdrew; SHA-1 is widely deployed and more secure than MD5, but cryptanalysts have identified attacks against it; the SHA-2 family improves on SHA-1, but is vulnerable to clashes as of 2011; and the US standards authority thought it "prudent" from a security perspective to develop a new standard to "significantly improve the robustness of NIST's overall hash algorithm toolkit." Thus, a hash function design competition was meant to select a new U.S. national standard, to be called SHA-3, by 2012. The competition ended on October 2, 2012, when the NIST announced that [Keccak](https://en.wikipedia.org/wiki/SHA-3) would be the new SHA-3 hash algorithm. Unlike block and stream ciphers that are invertible, cryptographic hash functions produce a hashed output that cannot be used to retrieve the original input data. Cryptographic hash functions are used to verify the authenticity of data retrieved from an untrusted source or to add a layer of security.

### [Public-key cryptography](https://en.wikipedia.org/wiki/Public-key_cryptography)

Symmetric-key cryptosystems use the same key for encryption and decryption of a message, although a message or group of messages can have a different key than others. A significant disadvantage of symmetric ciphers is the key management necessary to use them securely. Each distinct pair of communicating parties must, ideally, share a different key, and perhaps for each ciphertext exchanged as well. The number of keys required increases as the square of the number of network members, which very quickly requires complex key management schemes to keep them all consistent and secret.


In a groundbreaking 1976 paper, Whitfield Diffie and Martin Hellman proposed the notion of public-key (also, more generally, called asymmetric key) cryptography in which two different but mathematically related keys are used—a public key and a private key. A public key system is so constructed that calculation of one key (the 'private key') is computationally infeasible from the other (the 'public key'), even though they are necessarily related. Instead, both keys are generated secretly, as an interrelated pair. The historian David Kahn described public-key cryptography as "the most revolutionary new concept in the field since polyalphabetic substitution emerged in the Renaissance".

In public-key cryptosystems, the public key may be freely distributed, while its paired private key must remain secret. The public key is used for encryption, while the private or secret key is used for decryption. While Diffie and Hellman could not find such a system, they showed that public-key cryptography was indeed possible by presenting the [Diffie–Hellman key exchange](https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange) protocol, a solution that is now widely used in secure communications to allow two parties to secretly agree on a shared encryption key.

The X.509 standard defines the most commonly used format for public key certificates.

Diffie and Hellman's publication sparked widespread academic efforts in finding a practical public-key encryption system. This race was finally won in 1978 by [Ronald Rivest](https://en.wikipedia.org/wiki/Ron_Rivest), [Adi Shamir](https://en.wikipedia.org/wiki/Adi_Shamir), and Len Adleman, whose solution has since become known as the RSA algorithm.

The Diffie–Hellman and RSA algorithms, in addition to being the first publicly known examples of high-quality public-key algorithms, have been among the most widely used. Other asymmetric-key algorithms include the [Cramer–Shoup cryptosystem](https://en.wikipedia.org/wiki/Cramer%E2%80%93Shoup_cryptosystem), [ElGamal encryption](https://en.wikipedia.org/wiki/ElGamal_encryption), and various elliptic curve techniques.

A document published in 1997 by the Government Communications Headquarters (GCHQ), a British intelligence organization, revealed that cryptographers at GCHQ had anticipated several academic developments. Reportedly, around 1970, James H. Ellis had conceived the principles of asymmetric key cryptography. In 1973, [Clifford Cocks](https://en.wikipedia.org/wiki/Clifford_Cocks) invented a solution that was very similar in design rationale to RSA. In 1974, [Malcolm J. Williamson](https://en.wikipedia.org/wiki/Malcolm_J._Williamson) is claimed to have developed the [Diffie–Hellman key exchange](https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange).


[Public-key cryptography](https://en.wikipedia.org/wiki/Public-key_cryptography) is also used for implementing digital signature schemes. A digital signature is reminiscent of an ordinary signature; they both have the characteristic of being easy for a user to produce, but difficult for anyone else to forge. Digital signatures can also be permanently tied to the content of the message being signed; they cannot then be 'moved' from one document to another, for any attempt will be detectable. In digital signature schemes, there are two algorithms: one for signing, in which a secret key is used to process the message (or a hash of the message, or both), and one for verification, in which the matching public key is used with the message to check the validity of the signature. RSA and DSA are two of the most popular digital signature schemes. Digital signatures are central to the operation of public key infrastructures and many network security schemes (e.g., SSL/TLS, many [VPN](https://en.wikipedia.org/wiki/Virtual_private_network)s, etc.).

Public-key algorithms are most often based on the computational complexity of "hard" problems, often from number theory. For example, the hardness of RSA is related to the integer factorization problem, while Diffie–Hellman and DSA are related to the discrete logarithm problem. The security of elliptic curve cryptography is based on number theoretic problems involving elliptic curves. Because of the difficulty of the underlying problems, most public-key algorithms involve operations such as modular multiplication and exponentiation, which are much more computationally expensive than the techniques used in most block ciphers, especially with typical key sizes. As a result, public-key cryptosystems are commonly hybrid cryptosystems, in which a fast high-quality symmetric-key encryption algorithm is used for the message itself, while the relevant symmetric key is sent with the message, but encrypted using a public-key algorithm. Similarly, hybrid signature schemes are often used, in which a cryptographic hash function is computed, and only the resulting hash is digitally signed.

### Cryptographic hash functions

Cryptographic hash functions are functions that take a variable-length input and return a fixed-length output, which can be used in, for example, a digital signature. For a hash function to be secure, it must be difficult to compute two inputs that hash to the same value (collision resistance) and to compute an input that hashes to a given output (preimage resistance). [MD4](https://en.wikipedia.org/wiki/MD4) is a long-used hash function that is now broken; MD5, a strengthened variant of [MD4](https://en.wikipedia.org/wiki/MD4), is also widely used but broken in practice. The US National Security Agency developed the Secure Hash [Algorithm](https://en.wikipedia.org/wiki/Algorithm) series of MD5-like hash functions: SHA-0 was a flawed algorithm that the agency withdrew; SHA-1 is widely deployed and more secure than MD5, but cryptanalysts have identified attacks against it; the SHA-2 family improves on SHA-1, but is vulnerable to clashes as of 2011; and the US standards authority thought it "prudent" from a security perspective to develop a new standard to "significantly improve the robustness of NIST's overall hash algorithm toolkit." Thus, a hash function design competition was meant to select a new U.S. national standard, to be called SHA-3, by 2012. The competition ended on October 2, 2012, when the NIST announced that [Keccak](https://en.wikipedia.org/wiki/SHA-3) would be the new SHA-3 hash algorithm. Unlike block and stream ciphers that are invertible, cryptographic hash functions produce a hashed output that cannot be used to retrieve the original input data. Cryptographic hash functions are used to verify the authenticity of data retrieved from an untrusted source or to add a layer of security.

### [Cryptanalysis](https://en.wikipedia.org/wiki/Cryptanalysis)

The goal of cryptanalysis is to find some weakness or insecurity in a cryptographic scheme, thus permitting its subversion or evasion.

It is a common misconception that every encryption method can be broken. In connection with his WWII work at [Bell Labs](https://en.wikipedia.org/wiki/Bell_Labs), [Claude Shannon](https://en.wikipedia.org/wiki/Claude_Shannon) proved that the one-time pad cipher is unbreakable, provided the key material is truly random, never reused, kept secret from all possible attackers, and of equal or greater length than the message. Most ciphers, apart from the one-time pad, can be broken with enough computational effort by brute force attack, but the amount of effort needed may be exponentially dependent on the key size, as compared to the effort needed to make use of the cipher. In such cases, effective security could be achieved if it is proven that the effort required (i.e., "work factor", in Shannon's terms) is beyond the ability of any adversary. This means it must be shown that no efficient method (as opposed to the time-consuming brute force method) can be found to break the cipher. Since no such proof has been found to date, the one-time-pad remains the only theoretically unbreakable cipher. Although well-implemented one-time-pad encryption cannot be broken, traffic analysis is still possible.

There are a wide variety of cryptanalytic attacks, and they can be classified in any of several ways. A common distinction turns on what Eve (an attacker) knows and what capabilities are available. In a ciphertext-only attack, Eve has access only to the ciphertext (good modern cryptosystems are usually effectively immune to ciphertext-only attacks). In a known-plaintext attack, Eve has access to a ciphertext and its corresponding plaintext (or to many such pairs). In a chosen-plaintext attack, Eve may choose a plaintext and learn its corresponding ciphertext (perhaps many times); an example is gardening, used by the British during WWII. In a chosen-ciphertext attack, Eve may be able to choose ciphertexts and learn their corresponding plaintexts. Finally in a man-in-the-middle attack Eve gets in between Alice (the sender) and Bob (the recipient), accesses and modifies the traffic and then forward it to the recipient. Also important, often overwhelmingly so, are mistakes (generally in the design or use of one of the protocols involved).

[Cryptanalysis](https://en.wikipedia.org/wiki/Cryptanalysis) of symmetric-key ciphers typically involves looking for attacks against the block ciphers or stream ciphers that are more efficient than any attack that could be against a perfect cipher. For example, a simple brute force attack against DES requires one known plaintext and 255 decryptions, trying approximately half of the possible keys, to reach a point at which chances are better than even that the key sought will have been found. But this may not be enough assurance; a linear cryptanalysis attack against DES requires 243 known plaintexts (with their corresponding ciphertexts) and approximately 243 DES operations. This is a considerable improvement over brute force attacks.

Public-key algorithms are based on the computational difficulty of various problems. The most famous of these are the difficulty of integer factorization of semiprimes and the difficulty of calculating discrete logarithms, both of which are not yet proven to be solvable in polynomial time (P) using only a classical Turing-complete computer. Much public-key cryptanalysis concerns designing algorithms in P that can solve these problems, or using other technologies, such as quantum computers. For instance, the best-known algorithms for solving the elliptic curve-based version of discrete logarithm are much more time-consuming than the best-known algorithms for factoring, at least for problems of more or less equivalent size. Thus, to achieve an equivalent strength of encryption, techniques that depend upon the difficulty of factoring large composite numbers, such as the RSA cryptosystem, require larger keys than elliptic curve techniques. For this reason, public-key cryptosystems based on elliptic curves have become popular since their invention in the mid-1990s.

While pure cryptanalysis uses weaknesses in the algorithms themselves, other attacks on cryptosystems are based on actual use of the algorithms in real devices, and are called side-channel attacks. If a cryptanalyst has access to, for example, the amount of time the device took to encrypt a number of plaintexts or report an error in a password or PIN character, they may be able to use a timing attack to break a cipher that is otherwise resistant to analysis. An attacker might also study the pattern and length of messages to derive valuable information; this is known as traffic analysis and can be quite useful to an alert adversary. Poor administration of a cryptosystem, such as permitting too short keys, will make any system vulnerable, regardless of other virtues. Social engineering and other attacks against humans (e.g., bribery, extortion, blackmail, espionage, rubber-hose cryptanalysis or torture) are usually employed due to being more cost-effective and feasible to perform in a reasonable amount of time compared to pure cryptanalysis by a high margin.

### [Cryptographic primitive](https://en.wikipedia.org/wiki/Cryptographic_primitive)s

Much of the theoretical work in cryptography concerns cryptographic primitives—algorithms with basic cryptographic properties—and their relationship to other cryptographic problems. More complicated cryptographic tools are then built from these basic primitives. These primitives provide fundamental properties, which are used to develop more complex tools called cryptosystems or cryptographic protocols, which guarantee one or more high-level security properties. Note, however, that the distinction between cryptographic primitives and cryptosystems, is quite arbitrary; for example, the RSA algorithm is sometimes considered a cryptosystem, and sometimes a primitive. Typical examples of cryptographic primitives include pseudorandom functions, one-way functions, etc.

### Cryptosystems

One or more cryptographic primitives are often used to develop a more complex algorithm, called a cryptographic system, or cryptosystem. Cryptosystems (e.g., El-Gamal encryption) are designed to provide particular functionality (e.g., public key encryption) while guaranteeing certain security properties (e.g., chosen-plaintext attack (CPA) security in the random oracle model). Cryptosystems use the properties of the underlying cryptographic primitives to support the system's security properties. As the distinction between primitives and cryptosystems is somewhat arbitrary, a sophisticated cryptosystem can be derived from a combination of several more primitive cryptosystems. In many cases, the cryptosystem's structure involves back and forth communication among two or more parties in space (e.g., between the sender of a secure message and its receiver) or across time (e.g., cryptographically protected backup data). Such cryptosystems are sometimes called cryptographic protocols.

Some widely known cryptosystems include RSA, Schnorr signature, [ElGamal encryption](https://en.wikipedia.org/wiki/ElGamal_encryption), and [Pretty Good Privacy](https://en.wikipedia.org/wiki/Pretty_Good_Privacy) (PGP). More complex cryptosystems include electronic cash systems, signcryption systems, etc. Some more 'theoretical' cryptosystems include interactive proof systems, (like zero-knowledge proofs) and systems for secret sharing.

### Lightweight cryptography

Lightweight cryptography (LWC) concerns cryptographic algorithms developed for a strictly constrained environment. The growth of Internet of Things (IoT) has spiked research into the development of lightweight algorithms that are better suited for the environment. An IoT environment requires strict constraints on power consumption, processing power, and security. [Algorithm](https://en.wikipedia.org/wiki/Algorithm)s such as PRESENT, AES, and SPECK are examples of the many LWC algorithms that have been developed to achieve the standard set by the National Institute of Standards and Technology.

## Applications

Cryptography is widely used on the internet to help protect user-data and prevent eavesdropping. To ensure secrecy during transmission, many systems use private key cryptography to protect transmitted information. With public-key systems, one can maintain secrecy without a master key or a large number of keys. But, some algorithms like [Bit](https://en.wikipedia.org/wiki/Bit)Locker and VeraCrypt are generally not private-public key cryptography. For example, Veracrypt uses a password hash to generate the single private key. However, it can be configured to run in public-private key systems. The [C++](https://en.wikipedia.org/wiki/C%2B%2B) opensource encryption library OpenSSL provides free and opensource encryption software and tools. The most commonly used encryption cipher suit is AES, as it has hardware acceleration for all x86 based processors that has AES-NI. A close contender is [ChaCha20-[Poly1305](https://en.wikipedia.org/wiki/Poly1305)](https://en.wikipedia.org/wiki/ChaCha20-[Poly1305](https://en.wikipedia.org/wiki/Poly1305)), which is a stream cipher, however it is commonly used for mobile devices as they are ARM based which does not feature AES-NI instruction set extension.

### [Cybersecurity](https://en.wikipedia.org/wiki/Computer_security)

Cryptography can be used to secure communications by encrypting them. Websites use encryption via HTTPS. "End-to-end" encryption, where only sender and receiver can read messages, is implemented for email in [Pretty Good Privacy](https://en.wikipedia.org/wiki/Pretty_Good_Privacy) and for secure messaging in general in WhatsApp, Signal and Telegram.

Operating systems use encryption to keep passwords secret, conceal parts of the system, and ensure that software updates are truly from the system maker. Instead of storing plaintext passwords, computer systems store hashes thereof; then, when a user logs in, the system passes the given password through a cryptographic hash function and compares it to the hashed value on file. In this manner, neither the system nor an attacker has at any point access to the password in plaintext.

Encryption is sometimes used to encrypt one's entire drive. For example, University College London has implemented [Bit](https://en.wikipedia.org/wiki/Bit)Locker (a program by Microsoft) to render drive data opaque without users logging in.

### Cryptocurrencies and cryptoeconomics

Cryptographic techniques enable cryptocurrency technologies, such as distributed ledger technologies (e.g., blockchains), which finance cryptoeconomics applications such as decentralized finance (DeFi). Key cryptographic techniques that enable cryptocurrencies and cryptoeconomics include, but are not limited to: cryptographic keys, cryptographic hash function, asymmetric (public key) encryption, Multi-Factor [Authentication](https://en.wikipedia.org/wiki/Authentication) (MFA), End-to-End Encryption (E2EE), and Zero Knowledge Proofs (ZKP).

### [Quantum computing](https://en.wikipedia.org/wiki/Quantum_computing) cybersecurity

Estimates suggest that a quantum computer could reduce the effort required to break today’s strongest RSA or elliptic-curve keys from millennia to mere seconds, rendering current protocols (such as the versions of TLS that rely on those keys) insecure.

To mitigate this “quantum threat”, researchers are developing quantum-resistant algorithms whose security rests on problems believed to remain hard for both classical and quantum computers.

## Legal issues



### Prohibitions

Cryptography has long been of interest to intelligence gathering and law enforcement agencies. Secret communications may be criminal or even treasonous. Because of its facilitation of privacy, and the diminution of privacy attendant on its prohibition, cryptography is also of considerable interest to civil rights supporters. Accordingly, there has been a history of controversial legal issues surrounding cryptography, especially since the advent of inexpensive computers has made widespread access to high-quality cryptography possible.

In some countries, even the domestic use of cryptography is, or has been, restricted. Until 1999, France significantly restricted the use of cryptography domestically, though it has since relaxed many of these rules. In [China](https://en.wikipedia.org/wiki/China) and Iran, a license is still required to use cryptography. Many countries have tight restrictions on the use of cryptography. Among the more restrictive are laws in [Belarus](https://en.wikipedia.org/wiki/Belarus), Kazakhstan, Mongolia, Pakistan, Singapore, Tunisia, and Vietnam.

In the United States, cryptography is legal for domestic use, but there has been much conflict over legal issues related to cryptography. One particularly important issue has been the export of cryptography and cryptographic software and hardware. Probably because of the importance of cryptanalysis in World War II and an expectation that cryptography would continue to be important for national security, many Western governments have, at some point, strictly regulated export of cryptography. After World War II, it was illegal in the US to sell or distribute encryption technology overseas; in fact, encryption was designated as auxiliary military equipment and put on the United States Munitions List. Until the development of the personal computer, asymmetric key algorithms (i.e., public key techniques), and the Internet, this was not especially problematic. However, as the Internet grew and computers became more widely available, high-quality encryption techniques became well known around the globe.

### Export controls

In the 1990s, there were several challenges to US export regulation of cryptography. After the source code for Philip Zimmermann's [Pretty Good Privacy](https://en.wikipedia.org/wiki/Pretty_Good_Privacy) (PGP) encryption program found its way onto the Internet in June 1991, a complaint by [RSA Security](https://en.wikipedia.org/wiki/RSA_Security) (then called RSA Data Security, Inc.) resulted in a lengthy criminal investigation of Zimmermann by the US Customs Service and the FBI, though no charges were ever filed. [Daniel J. Bernstein](https://en.wikipedia.org/wiki/Daniel_J._Bernstein), then a graduate student at UC Berkeley, brought a lawsuit against the US government challenging some aspects of the restrictions based on free speech grounds. The 1995 case [Bernstein v. United States](https://en.wikipedia.org/wiki/Bernstein_v._United_States) ultimately resulted in a 1999 decision that printed source code for cryptographic algorithms and systems was protected as free speech by the United States Constitution.

In 1996, thirty-nine countries signed the Wassenaar Arrangement, an arms control treaty that deals with the export of arms and "dual-use" technologies such as cryptography. The treaty stipulated that the use of cryptography with short key-lengths (56-bit for symmetric encryption, 512-bit for RSA) would no longer be export-controlled. Cryptography exports from the US became less strictly regulated as a consequence of a major relaxation in 2000; there are no longer very many restrictions on key sizes in US-exported mass-market software. Since this relaxation in US export restrictions, and because most personal computers connected to the Internet include US-sourced web browsers such as Firefox or Internet Explorer, almost every Internet user worldwide has potential access to quality cryptography via their browsers (e.g., via Transport Layer Security). The Mozilla Thunderbird and Microsoft Outlook E-mail client programs similarly can transmit and receive emails via TLS, and can send and receive email encrypted with S/MIME. Many Internet users do not realize that their basic application software contains such extensive cryptosystems. These browsers and email programs are so ubiquitous that even governments whose intent is to regulate civilian use of cryptography generally do not find it practical to do much to control distribution or use of cryptography of this quality, so even when such laws are in force, actual enforcement is often effectively impossible.

### NSA involvement

Another contentious issue connected to cryptography in the United States is the influence of the National Security Agency on cipher development and policy. The NSA was involved with the design of DES during its development at IBM and its consideration by the National Bureau of Standards as a possible Federal Standard for cryptography. DES was designed to be resistant to differential cryptanalysis, a powerful and general cryptanalytic technique known to the NSA and IBM, that became publicly known only when it was rediscovered in the late 1980s. According to [Steven Levy](https://en.wikipedia.org/wiki/Steven_Levy), IBM discovered differential cryptanalysis, but kept the technique secret at the NSA's request. The technique became publicly known only when Biham and Shamir re-discovered and announced it some years later. The entire affair illustrates the difficulty of determining what resources and knowledge an attacker might actually have.

Another instance of the NSA's involvement was the 1993 [Clipper chip](https://en.wikipedia.org/wiki/Clipper_chip) affair, an encryption microchip intended to be part of the Capstone cryptography-control initiative. Clipper was widely criticized by cryptographers for two reasons. The cipher algorithm (called Skipjack) was then classified (declassified in 1998, long after the Clipper initiative lapsed). The classified cipher caused concerns that the NSA had deliberately made the cipher weak to assist its intelligence efforts. The whole initiative was also criticized based on its violation of Kerckhoffs's Principle, as the scheme included a special escrow key held by the government for use by law enforcement (i.e. wiretapping).

### Digital rights management

Cryptography is central to digital rights management (DRM), a group of techniques for technologically controlling use of copyrighted material, being widely implemented and deployed at the behest of some copyright holders. In 1998, U.S. President [Bill Clinton](https://en.wikipedia.org/wiki/Bill_Clinton) signed the Digital Millennium [Copyright](https://en.wikipedia.org/wiki/Copyright) Act (DMCA), which criminalized all production, dissemination, and use of certain cryptanalytic techniques and technology (now known or later discovered); specifically, those that could be used to circumvent DRM technological schemes. This had a noticeable impact on the cryptography research community since an argument can be made that any cryptanalytic research violated the DMCA. Similar statutes have since been enacted in several countries and regions, including the implementation in the EU [Copyright](https://en.wikipedia.org/wiki/Copyright) Directive. Similar restrictions are called for by treaties signed by World Intellectual Property Organization member-states.

The [United States Department of Justice](https://en.wikipedia.org/wiki/United_States_Department_of_Justice) and FBI have not enforced the DMCA as rigorously as had been feared by some, but the law, nonetheless, remains a controversial one. Niels Ferguson, a well-respected cryptography researcher, has publicly stated that he will not release some of his research into an Intel security design for fear of prosecution under the DMCA. Cryptologist [Bruce Schneier](https://en.wikipedia.org/wiki/Bruce_Schneier) has argued that the DMCA encourages vendor lock-in, while inhibiting actual measures toward cyber-security. Both Alan Cox (longtime [Linux kernel](https://en.wikipedia.org/wiki/Linux_kernel) developer) and Edward Felten (and some of his students at Princeton) have encountered problems related to the Act. Dmitry Sklyarov was arrested during a visit to the US from Russia, and jailed for five months pending trial for alleged violations of the DMCA arising from work he had done in Russia, where the work was legal. In 2007, the cryptographic keys responsible for [Blu-ray](https://en.wikipedia.org/wiki/Blu-ray) and [HD DVD](https://en.wikipedia.org/wiki/HD_DVD) content scrambling were discovered and released onto the Internet. In both cases, the Motion Picture Association of America sent out numerous DMCA takedown notices, and there was a massive Internet backlash triggered by the perceived impact of such notices on fair use and free speech.

### Forced disclosure of encryption keys

In the United Kingdom, the Regulation of Investigatory Powers Act gives UK police the powers to force suspects to decrypt files or hand over passwords that protect encryption keys. Failure to comply is an offense in its own right, punishable on conviction by a two-year jail sentence or up to five years in cases involving national security. Successful prosecutions have occurred under the Act; the first, in 2009, resulted in a term of 13 months' imprisonment. Similar forced disclosure laws in Australia, Finland, France, and India compel individual suspects under investigation to hand over encryption keys or passwords during a criminal investigation.

In the United States, the federal criminal case of United States v. Fricosu addressed whether a search warrant can compel a person to reveal an encryption passphrase or password. The [Electronic Frontier Foundation](https://en.wikipedia.org/wiki/Electronic_Frontier_Foundation) (EFF) argued that this is a violation of the protection from self-incrimination given by the Fifth Amendment. In 2012, the court ruled that under the [All Writs Act](https://en.wikipedia.org/wiki/All_Writs_Act), the defendant was required to produce an unencrypted hard drive for the court.

In many jurisdictions, the legal status of forced disclosure remains unclear.

The 2016 FBI–Apple encryption dispute concerns the ability of courts in the United States to compel manufacturers' assistance in unlocking cell phones whose contents are cryptographically protected.

As a potential counter-measure to forced disclosure some cryptographic software supports plausible deniability, where the encrypted data is indistinguishable from unused random data (for example such as that of a drive which has been securely wiped).

## Further reading



## External links


The dictionary definition of cryptography at Wiktionary
Media related to Cryptography at Wikimedia Commons
Cryptography on In Our Time at the [BBC](https://en.wikipedia.org/wiki/BBC)
Crypto Glossary and Dictionary of Technical Cryptography Archived 4 July 2022 at the Wayback Machine
A Course in Cryptography by Raphael Pass & Abhi Shelat – offered at Cornell in the form of lecture notes.

For more on the use of cryptographic elements in fiction, see: Dooley, John F. (23 August 2012). "Cryptology in Fiction". Archived from the original on 29 July 2020. Retrieved 20 February 2015.

The George Fabyan Collection at the Library of Congress has early editions of works of seventeenth-century English literature, publications relating to cryptography.

## References

- http://www.cryptolaw.org/cls2.htm
- http://www.pcworld.com/article/137881/uk_data_encryption_disclosure_law_takes_effect.html
- http://boingboing.net/2007/05/02/digg-users-revolt-ov.html
- https://books.google.com/books?id=cH-NGrpcIMcC&pg=PA6
- http://www-ee.stanford.edu/~hellman/publications/24.pdf
- http://www.fortify.net/related/cryptographers.html
- http://www.csrc.nist.gov/publications/fips/fips197/fips-197.pdf
- http://www.ncua.gov/Resources/Documents/LCU2004-09.pdf
- http://www.windowsecurity.com/articles/SSH.html
- https://web.archive.org/web/20080228075550/http://csrc.nist.gov/groups/ST/hash/documents/FR_Notice_Nov07.pdf
- https://www.nist.gov/itl/csd/sha-100212.cfm
- https://web.archive.org/web/20011116122233/http://theory.lcs.mit.edu/~rivest/rsapaper.pdf
- https://www.nytimes.com/library/cyber/week/122497encrypt.html
- http://www.fi.muni.cz/usr/matyas/lecture/paper2.pdf
- http://www8.cs.umu.se/education/examina/Rapporter/MattiasEriksson.pdf
- http://citeseer.ist.psu.edu/cache/papers/cs/22094/http:zSzzSzeprint.iacr.orgzSz2001zSz056.pdf/junod01complexity.pdf
- http://www.emc.com/emc-plus/rsa-labs/standards-initiatives/cryptographic-policies-countries.htm
- https://web.archive.org/web/20051201184530/http://www.cyberlaw.com/cylw1095.html
- http://www.ieee-security.org/[Cipher](https://en.wikipedia.org/wiki/Cipher)/Newsbriefs/1996/960214.zimmerman.html
- http://www.epic.org/crypto/export_controls/bernstein_decision_9_cir.html
- http://www.emc.com/emc-plus/rsa-labs/standards-initiatives/united-states-cryptography-export-import.htm
- http://www.schneier.com/crypto-gram-0006.html#DES
- http://domino.watson.ibm.com/tchjr/journalindex.nsf/0/94f78816c77fc77885256bfa0067fb98?OpenDocument
- http://www.copyright.gov/legislation/dmca.pdf
- https://web.archive.org/web/20011201184919/http://www.macfergus.com/niels/dmca/cia.html
- https://www.schneier.com/essays/archives/2001/08/arrest_of_computer_r.html
- https://www.theregister.co.uk/2009/11/24/ripa_jfl/
- http://www.denverpost.com/news/ci_19669803
- https://www.theregister.co.uk/2011/07/13/eff_piles_in_against_forced_decryption/
- https://www.wired.com/images_blogs/threatlevel/2012/01/decrypt.pdf
- http://www.iranicaonline.org/articles/codes-romuz-sg
- https://www.bis.doc.gov/index.php/documents/regulations-docs/445-category-5-part-2-information-security/file
- https://www.ssltrust.com.au/help/setup-guides/client-certificate-authentication
- https://web.archive.org/web/20150407153905/http://csrc.nist.gov/publications/fips/fips197/fips-197.pdf
- http://theory.lcs.mit.edu/~rivest/rsapaper.pdf
- http://www.cyberlaw.com/cylw1095.html
- http://www.macfergus.com/niels/dmca/cia.html
- https://archive.org/details/stealingsecretst00gann
- https://archive.org/details/codebookevolutio00sing
- https://archive.org/details/codebookevolutio00sing/page/279
- https://archive.org/details/Applied_Cryptography_2nd_ed._B._Schneier
- https://api.semanticscholar.org/CorpusID:123537702
- https://api.semanticscholar.org/CorpusID:13210741
- https://api.semanticscholar.org/CorpusID:2873616
- https://api.semanticscholar.org/CorpusID:206783462
- https://books.google.com/books?id=3S8rhOEmDIIC&q=david+kahn+the+codebreakers
- https://ieeexplore.ieee.org/document/9269083
- https://api.semanticscholar.org/CorpusID:227277538
- https://api.semanticscholar.org/CorpusID:232042514
- https://api.semanticscholar.org/CorpusID:21812933
- https://www.schneier.com/blog/archives/2004/10/the_legacy_of_d.html
- https://archive.org/details/codebook00simo/page/278
- https://archive.org/details/handbookofapplie0000mene
- https://web.archive.org/web/20120120135135/http://www.pcworld.com/article/137881/uk_data_encryption_disclosure_law_takes_effect.html
- https://www.journals.uchicago.edu/doi/10.1086/698861
- https://www.theregister.co.uk/2009/08/11/ripa_iii_figures/
- https://api.semanticscholar.org/CorpusID:165362817
- https://dl.acm.org/doi/10.1109/TIT.1976.1055638
- http://www.nature.com/articles/nature23461
- https://ui.adsabs.harvard.edu/abs/2017Natur.549..188B
- https://api.semanticscholar.org/CorpusID:4446249
- https://doi.org/10.1086%2F698861
- https://doi.org/10.1198%2Ftas.2011.10191
- https://doi.org/10.1080%2F0161-119291866801
- https://doi.org/10.1080%2F01611190802336097
- https://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.37.9720
- https://doi.org/10.1109%2Ftit.1976.1055638
- https://doi.org/10.1038%2Fnature23461
- https://pubmed.ncbi.nlm.nih.gov/28905891
- https://doi.org/10.1145%2F1499799.1499815
- https://doi.org/10.2307%2F20040343
- https://www.jstor.org/stable/20040343
- https://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.607.2677
- https://doi.org/10.1145%2F359340.359342
- https://doi.org/10.1007%2F3-540-45537-X_16
- https://doi.org/10.23919%2FCNSM50824.2020.9269083
- https://doi.org/10.1109%2FACCESS.2021.3052867
- https://doi.org/10.1147%2Frd.383.0243
- https://doi.org/10.1007%2Fbf00630563
- https://archive.org/details/codesintroductio00bigg_911
- https://archive.org/details/codesintroductio00bigg_911/page/n176
- https://web.archive.org/web/20130101062615/http://www.cryptolaw.org/cls2.htm
- https://web.archive.org/web/20150512030538/http://boingboing.net/2007/05/02/digg-users-revolt-ov.html
- https://web.archive.org/web/20220226185812/https://www.journals.uchicago.edu/doi/10.1086/698861
- https://web.archive.org/web/20170305113651/http://www.iranicaonline.org/articles/codes-romuz-sg
- https://web.archive.org/web/20230701101753/https://books.google.com/books?id=3S8rhOEmDIIC&q=david+kahn+the+codebreakers
- https://web.archive.org/web/20220223233956/https://www.schneier.com/blog/archives/2004/10/the_legacy_of_d.html
- https://web.archive.org/web/20171203090237/https://www-ee.stanford.edu/~hellman/publications/24.pdf
- https://web.archive.org/web/20150924014751/http://www.fortify.net/related/cryptographers.html
- https://web.archive.org/web/20220419150601/https://dl.acm.org/doi/10.1109/TIT.1976.1055638
- https://web.archive.org/web/20140912045940/http://www.ncua.gov/Resources/Documents/LCU2004-09.pdf
- https://web.archive.org/web/20091029164411/http://www.windowsecurity.com/articles/SSH.html
- https://web.archive.org/web/20220710194707/https://www.nature.com/articles/nature23461
- https://web.archive.org/web/20150402081721/http://www.nist.gov/itl/csd/sha-100212.cfm
- https://web.archive.org/web/20190826005346/https://www.ssltrust.com.au/help/setup-guides/client-certificate-authentication
- https://web.archive.org/web/20170627155400/http://www.nytimes.com/library/cyber/week/122497encrypt.html
- https://web.archive.org/web/20110727161329/http://www.fi.muni.cz/usr/matyas/lecture/paper2.pdf
- https://web.archive.org/web/20160603222024/http://www8.cs.umu.se/education/examina/Rapporter/MattiasEriksson.pdf
- https://web.archive.org/web/20210424034813/https://ieeexplore.ieee.org/document/9269083/
- https://web.archive.org/web/20150416025558/http://www.emc.com/emc-plus/rsa-labs/standards-initiatives/cryptographic-policies-countries.htm
- https://web.archive.org/web/20100611230953/http://www.ieee-security.org/[Cipher](https://en.wikipedia.org/wiki/Cipher)/Newsbriefs/1996/960214.zimmerman.html
- https://web.archive.org/web/20090813015456/http://epic.org/crypto/export_controls/bernstein_decision_9_cir.html
- https://web.archive.org/web/20180926085950/https://www.bis.doc.gov/index.php/documents/regulations-docs/445-category-5-part-2-information-security/file
- https://web.archive.org/web/20150331004104/http://www.emc.com/emc-plus/rsa-labs/standards-initiatives/united-states-cryptography-export-import.htm
- https://web.archive.org/web/20100102025613/http://schneier.com/crypto-gram-0006.html#DES
- https://web.archive.org/web/20160304061501/http://domino.watson.ibm.com/tchjr/journalindex.nsf/0/94f78816c77fc77885256bfa0067fb98?OpenDocument
- https://web.archive.org/web/20070808232655/http://www.copyright.gov/legislation/dmca.pdf
- https://web.archive.org/web/20150317130319/http://www.theregister.co.uk/2009/08/11/ripa_iii_figures/
- https://web.archive.org/web/20150326053131/http://www.theregister.co.uk/2009/11/24/ripa_jfl/
- https://web.archive.org/web/20150402121718/http://www.denverpost.com/news/ci_19669803
- https://web.archive.org/web/20141024034741/http://www.theregister.co.uk/2011/07/13/eff_piles_in_against_forced_decryption/
- https://web.archive.org/web/20210609162701/https://www.wired.com/images_blogs/threatlevel/2012/01/decrypt.pdf
- https://napier-surface.worktribe.com/2746967/1/Recent%20Advances%20and%20Trends%20in%20Lightweight%20Cryptography%20for%20IoT%20Security
- https://web.archive.org/web/20110726214409/http://ftp.se.kde.org/pub/security/docs/ecash/crypto93.ps.gz
- https://doi.org/10.1007%2F3-540-48329-2_26
- http://ftp.se.kde.org/pub/security/docs/ecash/crypto93.ps.gz
- https://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.130.3397
- https://doi.org/10.1145%2F22145.22192
- https://api.semanticscholar.org/CorpusID:17981195
- https://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.397.4002
- https://doi.org/10.1137%2F0218012
- https://doi.org/10.1145%2F359168.359176
- https://api.semanticscholar.org/CorpusID:16321225
- https://ui.adsabs.harvard.edu/abs/2021IEEEA...928177T
- https://web.archive.org/web/20160612190952/http://www.techrepublic.com/article/the-undercover-war-on-your-internet-secrets-how-online-surveillance-cracked-our-trust-in-the-web/
- http://www.techrepublic.com/article/the-undercover-war-on-your-internet-secrets-how-online-surveillance-cracked-our-trust-in-the-web/
- https://web.archive.org/web/20180226185448/https://blogs.ucl.ac.uk/infosec/2017/03/12/applications-of-cryptography/
- https://blogs.ucl.ac.uk/infosec/2017/03/12/applications-of-cryptography/
- https://web.archive.org/web/20170307204724/https://www.schneier.com/essays/archives/2001/08/arrest_of_computer_r.html
- https://web.archive.org/web/19990824044441/http://all.net/edu/curr/ip/Chap2-4.html
- https://web.archive.org/web/20220514061045/https://www.getapp.com/resources/common-encryption-methods/
- http://all.net/edu/curr/ip/Chap2-4.html
- https://www.getapp.com/resources/common-encryption-methods/
- https://doi.org/10.1109%2FTIT.1976.1055638
- https://www.govinfo.gov/content/pkg/FR-2007-11-02/pdf/E7-21581.pdf
- https://doi.org/10.1109%2FICECCPCE.2013.6998773
- https://api.semanticscholar.org/CorpusID:22378547
- https://www.bbc.co.uk/programmes/p004y272
- https://ciphersbyritter.com/GLOSSARY.HTM
- https://www.jstor.org/action/doBasicSearch?Query=%22Cryptography%22&acc=on&wc=on
- https://www.google.com/search?as_eq=wikipedia&q=%22Cryptography%22
- https://www.google.com/search?tbm=nws&q=%22Cryptography%22+-wikipedia&tbs=ar:1
- https://www.google.com/search?&q=%22Cryptography%22&tbs=bkt:s&tbm=bks
- https://www.google.com/search?tbs=bks:1&q=%22Cryptography%22+-wikipedia
- https://scholar.google.com/scholar?q=%22Cryptography%22
- https://web.archive.org/web/20110722183013/http://www.cryptool.org/download/CrypToolScript-en.pdf
- https://web.archive.org/web/20160809044453/http://www.wisdom.weizmann.ac.il/~oded/PSBookFrag/part2N.ps
- https://web.archive.org/web/20091016160136/http://www.cs.umd.edu/~jkatz/imc.html
- https://web.archive.org/web/20060709111152/http://www.crypto.rub.de/en_paar.html
- https://web.archive.org/web/20201031190651/http://cryptography-textbook.com/
- https://web.archive.org/web/20180501072701/http://www.mpepil.com/
- https://web.archive.org/web/20090924102944/http://www.cs.ucdavis.edu/~rogaway/classes/227/spring05/book/main.pdf
- https://web.archive.org/web/20220704220419/http://www.ciphersbyritter.com/GLOSSARY.HTM
- https://web.archive.org/web/20200729044734/http://faculty.knox.edu/jdooley/Crypto/CryptoFiction.htm
- https://www.wikidata.org/wiki/Q8789#identifiers
- http://www.cryptool.org/download/CrypToolScript-en.pdf
- http://www.wisdom.weizmann.ac.il/~oded/foc-book.html
- http://www.cs.umd.edu/~jkatz/imc.html
- http://www.cryptography-textbook.com/
- http://www.mpepil.com/
- http://www.cs.ucdavis.edu/~rogaway/classes/227/spring05/book/main.pdf
- http://www.csil.cn/upFiles/files/International%20Law.pdf
- https://ftl.toolforge.org/cgi-bin/ftl?st=wp&su=Cryptography&library=OLBP
- https://ftl.toolforge.org/cgi-bin/ftl?st=wp&su=Cryptography
- https://ftl.toolforge.org/cgi-bin/ftl?st=wp&su=Cryptography&library=0CHOOSE0
- https://www.cs.cornell.edu/courses/cs4830/2010fa/lecnotes.pdf
- http://faculty.knox.edu/jdooley/Crypto/CryptoFiction.htm
- https://www.loc.gov/rr/rarebook/coll/073.html
- https://catalogue.bnf.fr/ark:/12148/cb11941832r
- https://data.bnf.fr/ark:/12148/cb11941832r
- https://id.loc.gov/authorities/sh85034453
- https://aleph.nkp.cz/F/?func=find-c&local_base=aut&ccl_term=ica=ph127774&CON_LNG=ENG
- https://catalog.archives.gov/id/10644644
- https://search.worldcat.org/issn/0038-7134
- https://search.worldcat.org/oclc/567365751
- https://search.worldcat.org/issn/0028-0836
- https://search.worldcat.org/issn/2169-3536
- https://search.worldcat.org/oclc/244148644
- https://search.worldcat.org/oclc/16832704
- https://doi.org/10.1007%2F978-981-19-0920-7
- https://search.worldcat.org/oclc/48932608
- https://search.worldcat.org/oclc/891676484
- https://search.worldcat.org/oclc/183149167
- https://search.worldcat.org/oclc/56191935
- https://books.google.com/books?id=HvR0DgAAQBAJ
- https://books.google.com/books?id=cbl_BAAAQBAJ
- https://books.google.com/books?id=081H96F1enMC
- https://books.google.com/books?id=dG1rEAAAQBAJ&dq=most+important+cryptography+paper+shannon&pg=PR6
- https://books.google.com/books?id=fd2LtVgFzoMC&dq=claude+shannon+father+of+cryptography&pg=PA3
- https://www.nli.org.il/en/authorities/987007536087305171
- https://doi.org/10.17487%2FRFC2440
- https://datatracker.ietf.org/doc/html/rfc2440
- https://datos.bne.es/resource/XX4659806
- https://www.rfc-editor.org/rfc/rfc4880
- https://doi.org/10.1109%2FMARK.1979.8817296
- https://lux.collections.yale.edu/view/concept/4c6ea744-e838-4b89-84df-0d80813114e7
- https://www.ibm.com/think/topics/cryptography-use-cases
- https://spectrum.ieee.org/post-quantum-cryptography-2667758178
- https://ui.adsabs.harvard.edu/abs/1949mtc..book.....S
- https://doi.org/10.2307%2F2928778
- https://doi.org/10.1109%2FTHS.2011.6107841
- https://doi.org/10.17487%2FRFC2828
- https://api.semanticscholar.org/CorpusID:17915038
- https://web.archive.org/web/20151117030739/https://www.giac.org/paper/gsec/2604/introduction-modern-cryptosystems/104482
- https://web.archive.org/web/20220710193304/https://www.britannica.com/topic/cryptology
- https://www.jstor.org/stable/2928778
- https://books.google.com/books?id=sjhbAAAAMAAJ
- https://www.giac.org/paper/gsec/2604/introduction-modern-cryptosystems/104482
- https://www.britannica.com/topic/cryptology
- http://www.merriam-webster.com/dictionary/cryptology
- https://datatracker.ietf.org/doc/html/rfc2828
- https://www.rfc-editor.org/rfc/rfc4949
- https://www.rfc-editor.org/rfc/rfc2828
- https://www.military.com/join-armed-forces/army-cryptologic-linguist.html
- https://www.rfc-editor.org/rfc/rfc2440

## URL

https://en.wikipedia.org/wiki/Cryptography

