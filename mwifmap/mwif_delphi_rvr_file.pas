procedure ReadMassiveRiverLakesFile;
var
  PCol, PRow : Integer; // Indices into the pixels for a hex bitmap.
  I: Integer;

  function StripNextPixelRow : String;
  var
    PosC: Integer; // Position of next semicolon in string.
    L : Integer; // Length remaining after first value trimmed.
  begin
    PosC := Pos(';', S);

    Result := LeftStr(S, Pred(PosC)); // 1st value, excludes semicolon.
    L := Length(S) - Succ(Length(Result)); // Length remaining.
    S := RightStr(S, L); // Trim left value and semicolon.
  end;

// **************************************************************************** 
// ReadMassiveRiverLakesFile. 
// **************************************************************************** 
begin
  Readln(FRL, S); // Read one line/hex of data.
  S1 := StripNextPixelRow; // Remove row and column information.
      (*
      // ****************************************************************************
      // Check if the stored river/lake bitmap is for the correct hex.
      // ****************************************************************************
      ReadRow := StrToInt(TrimString(S1)); // Extract the row #.
      ReadColumn := StrToInt(S1); // Extract the column #.

      if (Row <> ReadRow) or (Column <> ReadColumn) then
      begin
      L2 := 6;
      Exit;
      end;
       *)
      // ****************************************************************************
      // Set location to the place in the CoastalBitMaps list of bitmap pointers.
      // ****************************************************************************
  Location := AddToPtr(RiverLakeBits, Pred(Place) * SizeOf(TRiverBits));

  for PRow := 1 to 152 do // Read each row of the bits from the file.
  begin
    RowLocation := AddToPtr(RiverLakeSkipRow, ((Pred(Place) * 152) + Pred(PRow)) * SizeOf(Boolean));

    S1 := StripNextPixelRow; // Take 1 pixel row worth of data from S.

    PCol := 1;
    while PCol < 18 do // 17 * 8 = 136 pixels.
    begin
      S2 := TrimString(S1); // Get next entry and trim remaining string.
      Found := False; // Assume no letter code is found.

      if Length(S2) = 1 then // All letter codes are single characters.
      begin
        for I := 17 downto 1 do // For each letter code.
        begin
          if S2 = LetterCode[I] then
          begin // Check for skipping the entire row.
            if S2 = 'Q' then Boolean(RowLocation^) := True
            else Boolean(RowLocation^) := False;

            ZeroCount := I; // How many groups of 8 to skip.
            Found := True;
            Break;
          end;
        end;
      end;

      if Found then // Letter code found. Use ZeroCount to write out zeros.
      begin
        for I := PCol to PCol + Pred(ZeroCount) do RiverB[I, PRow] := 0;
        Inc(PCol, ZeroCount);
      end
      else
      begin // Number found, transfer data on line to RiverB.
        Boolean(RowLocation^) := False;
        RiverB[PCol, PRow] := StrToInt(S2);
        Inc(PCol);
      end;
    end; // End of for each 8 bits in the row (PCol).
  end; // End of all 152 rows.
      // ****************************************************************************
      // Transfer the single set of river bits into the aggregate data storage.
      // ****************************************************************************

  for PRow := 1 to 152 do
    for PCol := 1 to 17 do
      TRiverBits(Location^)[PCol, PRow] := RiverB[PCol, PRow];
end;
