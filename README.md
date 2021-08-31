# Macula

Experimental python optimistic rollup fraud-proof generation tech by @protolambda.

Working on a python version for brevity and simplicity.
See previous [Go-experiment](https://github.com/protolambda/opti) for incomplete but faster Go implementation.
Inconvenient Merkle-Patricia-Trie access of ethereum state is the main drawback of python, maybe the Go version makes a comeback.

Q: Difference with Optimism OVM?
A: pure 1:1 EVM, but interactive fraud proof.

Q: Difference with Arbitrum AVM?
A: Also interactive fraud proof, but no AVM extras, no compiler, simplicity first.
Maintain 1:1 EVM for tooling ease and hopeful for later L1 non-interactive replacement.

Q: Why is it named Mucula?
A: The [Macula](https://en.wikipedia.org/wiki/Macula_of_retina) is the spot of the retina for color vision.
No optimism without color, no proof without optical vision. 


## License

LGPL v3, see [`LICENSE`](./LICENSE) file. The EVM design is based on the [go-ethereum EVM](https://github.com/ethereum/go-ethereum/tree/master/core/vm).
