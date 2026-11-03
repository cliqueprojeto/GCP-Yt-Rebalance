# GCP Yt Rebalance

Desenvolvido por Bruno Albertini  
[Gestão Cultural Pro](https://gestaoculturalpro.com.br)

Aplicativo desktop experimental para importação, download autorizado, conversão e separação local de áudio. Idioma inicial: pt-BR. Sem conta, assinatura ou processamento em nuvem.

**Estado: instaladores 0.3.0 reais para teste privado em Windows x64, macOS Intel, macOS ARM64 e Linux amd64 DEB. Os testes nativos de instalação e funcionamento passaram nos runners; o motor ainda não foi aprovado na matriz musical da POC. Mac sem Developer ID/notarização, e testes físicos Intel/M1 e Linux Mint pendentes.**

A versão 0.3 unifica logo e ícone, inicia WAV em 16 bits, carrega idiomas de legendas, salva padrões de qualidade e permite restaurar as configurações de fábrica. Mantém downloads, separação CPU, conversões, fila, estimativa, histórico e rolagem. Instalador completo: `dist/GCP Yt Rebalance Setup 0.3.0.exe`. [Instruções e testes 0.3](docs/teste-windows-v03.md). [Pipeline e pendências Mac/Linux](docs/build-multiplataforma.md). As versões anteriores foram preservadas em `dist/`. Player A/B e GPU ainda não estão implementados.

- [Diagnóstico e milestones](docs/diagnostico.md)
- [Arquitetura proposta](docs/arquitetura.md)
- [Protocolo e matriz da POC](docs/poc.md)
- [Identidade visual](assets/branding/README.md)
- [Resultados e pendências das Fases 0–1](docs/relatorio-fases-0-1.md)
- [Instaladores Mac/Linux: testes, tamanhos, hashes e instruções](docs/teste-macos-linux-v03.md)
- [Arch Linux privado: instalar com pacman ou reconstruir com PKGBUILD](packaging/arch/README.md)
- [Release privada 0.3.0: arquivos, checksums e validação](docs/release-v0.3.0.md)

## Ferramentas executáveis desta etapa

Python de desenvolvimento com Pillow para os ícones; NumPy para métricas. A POC exige dependências de ML isoladas. Essas ferramentas são para desenvolvimento, não requisitos previstos para o usuário final.

```powershell
python scripts/branding.py
python -m unittest discover -s tests -v
python scripts/poc_environment.py
python scripts/poc_onnx.py --out artifacts/onnx-probe
```

Os scripts não enviam áudio à rede. O teste ONNX usa pesos aleatórios e não mede qualidade de separação. Aquisição de dependências/pesos é uma etapa explícita de desenvolvimento. Nenhum arquivo de música deverá entrar no pacote final sem licença específica.

Licença do aplicativo: pendente de decisão do titular. Não há concessão de licença pública nesta etapa.
