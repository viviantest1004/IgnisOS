@echo -off
echo IgnisOS UEFI boot...
for %b run (0 5)
  if exist FS%b:\EFI\BOOT\BOOTAA64.EFI then
    FS%b:\EFI\BOOT\BOOTAA64.EFI
  endif
endfor
